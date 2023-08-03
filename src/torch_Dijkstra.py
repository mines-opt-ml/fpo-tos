"""
Implementation of Dijkstra for Pytorch. Adapted from Tensorflow version available at 
https://github.com/google-research/google-research/blob/master/perturbations/experiments/shortest_path.py

"""

import numpy as np
import torch
import heapq
import itertools


class Dijkstra:
  """Shortest path on a grid using Dijkstra's algorithm."""

  def __init__(
      self, four_neighbors=False, initial_cost=1e10, euclidean_weight=False):
    self.four_neighbors = four_neighbors
    self.initial_cost = initial_cost
    self.euclidean_weight = euclidean_weight

  def inside(self, x, y):
    return 0 <= x < self.shape[0] and 0 <= y < self.shape[1]

  def valid_move(self, x, y, off_x, off_y):
    size = np.sum(np.abs([off_x, off_y]))
    return ((size > 0) and
            (not self.four_neighbors or size == 1) and
            self.inside(x + off_x, y + off_y))

  def around(self, x, y):
    coords = itertools.product(range(-1, 2), range(-1, 2))
    result = []
    for offset in coords:
      if self.valid_move(x, y, offset[0], offset[1]):
        result.append((x + offset[0], y + offset[1]))
    return result

  def reset(self, costs):
    """Resets the variables to compute the shortest path of a cost matrix."""
    self.shape = costs.shape
    self.start = (0, 0)
    self.path_list = []  # Custom. To ensure compatibility 
    # of training data with DYS approach.
    self.end = (self.shape[0] - 1, self.shape[1] - 1)

    self.solution = np.ones(self.shape) * self.initial_cost
    self.solution[self.start] = 0.0

    self.queue = [(0.0, self.start)]
    self.visits = set(self.start)
    self.moves = dict()

    self.path = np.zeros(self.shape)
    self.path[self.start] = 1.0
    self.path[self.end] = 1.0

  def run_single(self, costs, Gen_Data=False):
    """Computes the shortest path on a single cost matrix."""
    self.reset(costs)
    while self.queue:
      _, (x, y) = heapq.heappop(self.queue)
      if (x, y) in self.visits:
        continue

      for nx, ny in self.around(x, y):
        if (nx, ny) in self.visits:
          continue

        if self.euclidean_weight:
          weight = np.sqrt((nx - x) ** 2 + (ny - y) ** 2)
        else:
          weight = 1.0
        new_cost = weight * costs[nx, ny] + self.solution[x, y]
        if new_cost < self.solution[nx, ny]:
          self.solution[nx, ny] = new_cost
          self.moves[(nx, ny)] = (x, y)
          heapq.heappush(self.queue, (new_cost, (nx, ny)))
      self.visits.add((x, y))

    curr = self.end
    # print(self.end)
    # print(curr)
    self.path_list.append((curr[0]+0.5, curr[1]+ 0.5))
    # print(self.path_list)
    while curr != self.start:
      curr = self.moves[curr]
      self.path[curr] = 1.0
      self.path_list.append((curr[0]+0.5, curr[1]+ 0.5))
      # print(self.path_list)
    
    if Gen_Data:
      return self.path, self.path_list
    else:
      return torch.from_numpy(self.path).float()

  def run_batch(self, tensor):
    return torch.stack([self.run_single(tensor[i])
                     for i in range(tensor.shape[0])],
                    axis=0)

  def __call__(self, tensor):
    if len(tensor.shape) > 3:
      return torch.stack([self.run_batch(tensor[i])
                       for i in range(tensor.shape[0])],
                      axis=0)
    if len(tensor.shape) == 3:
      return self.run_batch(tensor)
    return self.run_single(tensor)


def shift(x, i, j, pad_value = 0.0):
  """Shifts an input image of some rows and columns and padding with a value.
  Args:
   x: tf.Tensor the input tensor image.
   i: (int) number of rows to shift (can be negative).
   j: (int) number of columns to shift (can be negative).
   pad_value: (float) the value to for padding.
  Returns:
   A tensor of the same size as the input.
  """

  def _shift(z):
    """Shifts and pads with zeros."""
    offset_i = i if i > 0 else 0
    offset_j = j if j > 0 else 0
    if z.shape.rank < 3:
      z = tf.expand_dims(z, axis=2)
    result = tf.image.pad_to_bounding_box(
        z, offset_i, offset_j,
        tf.shape(z)[0] + np.abs(i), tf.shape(z)[1] + np.abs(j))
    result = tf.image.crop_to_bounding_box(
        result, tf.maximum(0, -i), tf.maximum(0, -j),
        tf.shape(z)[0], tf.shape(z)[1])
    return tf.squeeze(result)

  result = _shift(x)
  if pad_value != 0.0:
    pad = tf.cast((1 - _shift(tf.ones(x.shape))) * pad_value, x.dtype)
    result = result + pad

  return result
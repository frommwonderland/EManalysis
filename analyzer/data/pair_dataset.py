import numpy as np
import glob
import random
import torch
import torch.utils.data
from analyzer.data.data_raw import *
from analyzer.data.data_misc import *
from analyzer.data.data_vis import *
from analyzer.data.augmentation import Augmentor

class PairDataset():
    '''
    This Dataloader will prepare sample that are pairs for feeding the contrastive
    learning algorithm.
    '''
    def __init__(self, cfg):
        self.cfg = cfg
        #self.volume = self.cfg
        self.volume, self.label = self.get_input()
        self.sample_volume_size = (129, 129, 129)
        self.sample_stride = (1, 1, 1)
        self.augmentor = Augmentor(self.sample_volume_size)

        # Data information
        self.volume_size = [np.array(self.volume.shape)]
        self.sample_volume_size = np.array(self.sample_volume_size).astype(int)
        self.sample_stride = np.array(self.sample_stride).astype(int)
        self.sample_size = [count_volume(self.volume_size[x], self.sample_volume_size, self.sample_stride)
                            for x in range(len(self.volume_size))]
        self.sample_num = np.array([np.prod(x) for x in self.sample_size])
        self.sample_num_a = np.sum(self.sample_num)
        self.sample_num_c = np.cumsum([0] + list(self.sample_num))

        self.num_augmented_images = 2
        pos, vol = self.create_chunk_volume()
        print(vol.shape)
        print(vol)

    def __len__(self):
        pass

    def __getitem__(self, idx):
        sample_pair = self._create_sample_pair()
        return sample_pair

    def create_sample_pair(self):
        '''Create a sample pair that will be used for contrastive learning.
        '''
        sample_pair = list()
        _, sample = self.create_chunk_volume()

        # sample = self._random_sampling(self.sample_volume_size)
        # pos, out_volume, out_label, out_valid = sample
        # out_volume = self._create_masked_input(out_volume, out_label)

        # data = {'image': out_volume}
        # for i in range(self.num_augmented_images):
        #     augmented = self.augmentor(sample)
        #     sample_pair.append(augmented['image'])

        x1, x2 = self.augmentor(sample)

        return sample_pair

    def create_chunk_volume(self):
        '''
        Function creates small chunk from input volume that is processed
        into the training model.
        '''
        pos = self.get_pos(self.sample_volume_size)
        pos, out_vol, out_label = self.crop_with_pos(pos, self.sample_volume_size)
        return pos, self.create_masked_input(out_vol, out_label)

    def create_masked_input(self, vol: np.ndarray, label: np.ndarray) -> np.ndarray:
        '''
        Create masked input volume, that is pure EM where the mask is not 0. Otherwise all
        values set to 0. Returns the prepared mask.
        :params vol (numpy.ndarray): volume that is EM input.
        :params label (numpy.ndarray): associated label volume.
        '''
        vol[np.where(label == 0)] = 0
        return vol

    def get_input(self):
        '''Get input volume and labels.'''
        emfns = sorted(glob.glob(self.cfg.DATASET.EM_PATH + '*.' + self.cfg.DATASET.FILE_FORMAT))
        labelfns = sorted(glob.glob(self.cfg.DATASET.LABEL_PATH + '*.' + self.cfg.DATASET.FILE_FORMAT))
        if len(emfns) == 1:
            vol = readvol(emfns[0])
            label = readvol(labelfns[0])
        else:
            pass
        return vol, label

    def crop_with_pos(self, pos, vol_size):
        out_volume = (crop_volume(
            self.volume, vol_size, pos[1:])/255.0).astype(np.float32)
        out_label = crop_volume(
            self.label, vol_size, pos[1:])
        return pos, out_volume, out_label

    def get_pos(self, vol_size):
        pos = [0, 0, 0, 0]
        # pick a dataset
        did = self.index_to_dataset(random.randint(0, self.sample_num - 1))
        pos[0] = did
        # pick a position
        tmp_size = count_volume(
            self.volume_size[did], vol_size, self.sample_stride)
        tmp_pos = [random.randint(0, tmp_size[x]-1) * self.sample_stride[x]
                   for x in range(len(tmp_size))]

        pos[1:] = tmp_pos
        return pos

    def index_to_dataset(self, index):
        return np.argmax(index < self.sample_num_c) - 1
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on 23/10/17

@author: Maurizio Ferrari Dacrema
"""

from Base.Recommender import Recommender
from Base.Recommender_utils import check_matrix
from Base.SimilarityMatrixRecommender import SimilarityMatrixRecommender
from Base.IR_feature_weighting import okapi_BM_25, TF_IDF
from Support_functions import get_evaluate_data as ged
import numpy as np
import os, pickle

from Base.Similarity.Compute_Similarity import Compute_Similarity


class ItemKNNCBFRecommender(SimilarityMatrixRecommender, Recommender):
    """ ItemKNN recommender"""

    RECOMMENDER_NAME = "ItemKNNCBFRecommender"

    FEATURE_WEIGHTING_VALUES = ["BM25", "TF-IDF", "none"]

    def __init__(self, ICM, URM_train, sparse_weights=True):
        super(ItemKNNCBFRecommender, self).__init__()

        self.ICM = ICM.copy()

        # CSR is faster during evaluation
        self.URM_train = check_matrix(URM_train.copy(), 'csr')

        self.sparse_weights = sparse_weights
        self.W_sparse = None

    def __str__(self):
        return "Item Content Based (tokK={}, shrink={}, feature_weigthing_index={}".format(
            self.topK, self.shrink, self.feature_weighting_index)

    def fit(self, topK=50, shrink=100, similarity='cosine', normalize=True, force_compute_sim=True,
            feature_weighting="none", feature_weighting_index=0, **similarity_args):

        self.feature_weighting_index = feature_weighting_index
        feature_weighting = self.FEATURE_WEIGHTING_VALUES[feature_weighting_index]
        self.topK = topK
        self.shrink = shrink

        if not force_compute_sim:
            found = True
            try:
                with open(os.path.join("IntermediateComputations", "ICB",
                                       "tot={}_topK={}_shrink={}_featureweight={}.pkl".format(
                                               str(len(self.URM_train.data)), str(self.topK), str(self.shrink),
                                               str(self.feature_weighting_index))), 'rb') as handle:
                    (topK_new, shrink_new, W_sparse_new) = pickle.load(handle)
            except FileNotFoundError:
                print("File {} not found".format(os.path.join("IntermediateComputations", "ContentBFMatrix.pkl")))
                found = False

            if found and self.topK == topK_new and self.shrink == shrink_new:
                self.W_sparse = W_sparse_new
                print("Saved CBF Similarity Matrix Used!")
                return

        if feature_weighting not in self.FEATURE_WEIGHTING_VALUES:
            raise ValueError(
                "Value for 'feature_weighting' not recognized. Acceptable values are {}, provided was '{}'".format(
                    self.FEATURE_WEIGHTING_VALUES, feature_weighting))

        if feature_weighting == "BM25":
            self.ICM = self.ICM.astype(np.float32)
            self.ICM = okapi_BM_25(self.ICM)

        elif feature_weighting == "TF-IDF":
            self.ICM = self.ICM.astype(np.float32)
            self.ICM = TF_IDF(self.ICM)

        similarity = Compute_Similarity(self.ICM.T, shrink=shrink, topK=topK, normalize=normalize,
                                        similarity=similarity, **similarity_args)

        if self.sparse_weights:
            self.W_sparse = similarity.compute_similarity()

            with open(os.path.join("IntermediateComputations", "ICB",
                                   "tot={}_topK={}_shrink={}_featureweight={}.pkl".format(str(len(self.URM_train.data)),
                                                                                          str(self.topK),
                                                                                          str(self.shrink), str(
                                                   self.feature_weighting_index))), 'wb') as handle:
                pickle.dump((self.topK, self.shrink, self.W_sparse), handle, protocol=pickle.HIGHEST_PROTOCOL)
                print("CBF similarity matrix saved")
        else:
            self.W = similarity.compute_similarity()
            self.W = self.W.toarray()

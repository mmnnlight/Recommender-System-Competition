#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on 23/10/17

@author: Maurizio Ferrari Dacrema
"""
import os
import pickle

from Base.Recommender import Recommender
from Base.Recommender_utils import check_matrix
from Base.SimilarityMatrixRecommender import SimilarityMatrixRecommender

from Base.Similarity.Compute_Similarity import Compute_Similarity


class UserKNNCBRecommender(SimilarityMatrixRecommender, Recommender):
    """ UserKNN recommender"""

    RECOMMENDER_NAME = "UserKNNCBRecommender"

    def __init__(self, UCM_train, URM_train, sparse_weights=True):
        super(UserKNNCBRecommender, self).__init__()

        # Not sure if CSR here is faster
        self.URM_train = check_matrix(URM_train, 'csr')
        self.UCM_train = check_matrix(UCM_train, 'csr')
        self.dataset = None

        self.sparse_weights = sparse_weights

        self.compute_item_score = self.compute_score_user_based

    def fit(self, topK=350, shrink=10, similarity='cosine', normalize=True, force_compute_sim=True, **similarity_args):

        self.topK = topK
        self.shrink = shrink

        if not force_compute_sim:
            found = True
            try:
                with open(os.path.join("IntermediateComputations", "UCMCBFSimMatrix.pkl"), 'rb') as handle:
                    (topK_new, shrink_new, W_sparse_new) = pickle.load(handle)
            except FileNotFoundError:
                found = False

            if found and self.topK == topK_new and self.shrink == shrink_new:
                self.W_sparse = W_sparse_new
                print("Saved User CF Similarity Matrix Used!")
                return

        similarity = Compute_Similarity(self.UCM_train.T, shrink=shrink, topK=topK, normalize=normalize,
                                        similarity=similarity, **similarity_args)

        if self.sparse_weights:
            self.W_sparse = similarity.compute_similarity()
            with open(os.path.join("IntermediateComputations", "UCMCBFSimMatrix.pkl"), 'wb') as handle:
                pickle.dump((self.topK, self.shrink, self.W_sparse), handle, protocol=pickle.HIGHEST_PROTOCOL)
        else:
            self.W = similarity.compute_similarity()
            self.W = self.W.toarray()
import pickle
import sys

import time
from scipy import sparse

from Dataset.RS_Data_Loader import RS_Data_Loader
from KNN.HybridRecommenderXGBoost import HybridRecommenderXGBoost
from KNN.ItemKNNCFPageRankRecommender import ItemKNNCFPageRankRecommender
from MatrixFactorization.MatrixFactorization_RMSE import IALS_numpy
from SLIM_BPR.Cython.SLIM_BPR_Cython import SLIM_BPR_Cython
from SLIM_ElasticNet.SLIMElasticNetRecommender import SLIMElasticNetRecommender

from MatrixFactorization.Cython.MatrixFactorization_Cython import MatrixFactorization_BPR_Cython, \
    MatrixFactorization_FunkSVD_Cython, MatrixFactorization_AsySVD_Cython
from MatrixFactorization.PureSVD import PureSVDRecommender

from Base.NonPersonalizedRecommender import TopPop, Random

import numpy as np

from KNN.UserKNNCFRecommender import UserKNNCFRecommender
from KNN.HybridRecommenderTopNapproach import HybridRecommenderTopNapproach
from KNN.ItemKNNCFRecommender import ItemKNNCFRecommender
from KNN.HybridRecommender import HybridRecommender
from KNN.ItemKNNCBFRecommender import ItemKNNCBFRecommender
from KNN.UserKNNCBFRecommender import UserKNNCBRecommender
import Support_functions.get_evaluate_data as ged
from GraphBased.RP3betaRecommender import RP3betaRecommender
from GraphBased.P3alphaRecommender import P3alphaRecommender
import xgboost as xgb
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import make_classification
import traceback, os

import Support_functions.manage_data as md
from run_parameter_search import delete_previous_intermediate_computations


def run():
    evaluate_algorithm = False
    delete_old_computations = False
    slim_after_hybrid = False

    # delete_previous_intermediate_computations()
    # if not evaluate_algorithm:
    #     delete_previous_intermediate_computations()
    # else:
    #     print("ATTENTION: old intermediate computations kept, pay attention if running with all_train")
    # delete_previous_intermediate_computations()
    filename = "hybrid_ICB_ICF_UCF_IALS_SLIM_ELASTIC_local_08147.csv"

    dataReader = RS_Data_Loader(all_train=not evaluate_algorithm)

    URM_train = dataReader.get_URM_train()
    URM_PageRank_train = dataReader.get_page_rank_URM()
    URM_validation = dataReader.get_URM_validation()
    URM_test = dataReader.get_URM_test()
    ICM = dataReader.get_ICM()
    UCM_tfidf = dataReader.get_tfidf_artists()
    # _ = dataReader.get_tfidf_album()

    recommender_list1 = [
        # Random,
        # TopPop,
        ItemKNNCBFRecommender,
        # UserKNNCBRecommender,
        ItemKNNCFRecommender,
        UserKNNCFRecommender,
        # P3alphaRecommender,
        # RP3betaRecommender,
        # MatrixFactorization_BPR_Cython,
        # MatrixFactorization_FunkSVD_Cython,
        IALS_numpy,
        SLIM_BPR_Cython,
        # ItemKNNCFRecommenderFAKESLIM,
        # PureSVDRecommender,
        SLIMElasticNetRecommender
    ]

    from Base.Evaluation.Evaluator import SequentialEvaluator

    evaluator = SequentialEvaluator(URM_test, URM_train, exclude_seen=True)

    output_root_path = "result_experiments/"

    # If directory does not exist, create
    if not os.path.exists(output_root_path):
        os.makedirs(output_root_path)

    logFile = open(output_root_path + "result_all_algorithms.txt", "a")

    try:
        recommender_class = HybridRecommender
        print("Algorithm: {}".format(recommender_class))

        '''
        Our optimal run
        '''
        recommender_list = recommender_list1  # + recommender_list2  # + recommender_list3

        onPop = False

        # On pop it used to choose if have dynamic weights for
        recommender = recommender_class(URM_train, ICM, recommender_list, URM_PageRank_train=URM_PageRank_train,
                                        dynamic=False, UCM_train=UCM_tfidf,
                                        URM_validation=URM_validation, onPop=onPop)

        lambda_i = 0.1
        lambda_j = 0.05
        old_similrity_matrix = None
        num_factors = 395
        l1_ratio = 1e-06

        # Variabili secondo intervallo
        alphaRP3_2 = 0.9223827655310622
        betaRP3_2 = 0.2213306613226453
        num_factors_2 = 391

        recommender.fit(**
                        {
                            "topK": [10, 33, 160, -1, 761, 490],
                            "shrink": [8, 26, 2, -1, -1, -1],
                            "pop": [280],
                            "weights": [0.4144102812948438, 1.2692622265271245, 0.5932754240083344, 1.156343707405323,
                                        0.16827512618992413, 1.095104406726166],
                            "final_weights": [1, 1],
                            "force_compute_sim": False,  # not evaluate_algorithm,
                            "feature_weighting_index": 0,
                            "epochs": 150,
                            'lambda_i': [0.0], 'lambda_j': [1.0153577332223556e-08], 'SLIM_lr': [0.1],
                            'alphaP3': [0.4121720883248633],
                            'alphaRP3': [0.8582865731462926],
                            'betaRP': [0.2814208416833668],
                            'l1_ratio': 3.020408163265306e-06,
                            'alpha': 0.0014681984611695231,
                            'tfidf': [True],
                            "weights_to_dweights": -1,
                            "IALS_num_factors": 290,
                            "IALS_reg": 0.001,
                            "IALS_iters": 6,
                            "IALS_scaling": 'log',
                            "IALS_alpha": 40,
                            "filter_top_pop_len": 0})

        print("TEST")

        print("Starting Evaluations...")
        # to indicate if plotting for lenght or for pop

        results_run, results_run_string, target_recommendations = evaluator.evaluateRecommender(recommender,
                                                                                                plot_stats=False,
                                                                                                onPop=onPop)

        print("Algorithm: {}, results: \n{}".format([rec.RECOMMENDER_NAME for rec in recommender.recommender_list],
                                                    results_run_string))
        logFile.write("Algorithm: {}, results: \n{} time: {}".format(
            [rec.RECOMMENDER_NAME for rec in recommender.recommender_list], results_run_string, time.time()))
        logFile.flush()

        if not evaluate_algorithm:
            target_playlist = dataReader.get_target_playlist()
            md.assign_recomendations_to_correct_playlist(target_playlist, target_recommendations)
            md.make_CSV_file(target_playlist, filename)
            print('File {} created!'.format(filename))


    except Exception as e:
        traceback.print_exc()
        logFile.write("Algorithm: {} - Exception: {}\n".format(recommender_class, str(e)))
        logFile.flush()


#
# if not evaluate_algorithm:
#     delete_previous_intermediate_computations()

if __name__ == '__main__':
    run()

import pandas as pd
import numpy as np
from scipy.sparse import csr_matrix
import os, pickle
from itertools import repeat

from sklearn.feature_extraction.text import TfidfTransformer


def divide_train_test(train_old, threshold=0.8):
    msk = np.random.rand(len(train_old)) < threshold
    train = train_old[msk]
    test = train_old[~msk]
    return train, test


def make_series(test):
    dict_train = test.groupby(test.playlist_id).track_id
    test_songs_per_playlist = pd.Series(dict_train.apply(list))
    return test_songs_per_playlist


def tracks_popularity(URM_train):
    URM_train_csc = URM_train.copy().tocsc()
    songs_popularity = np.diff(URM_train_csc.indptr)
    del URM_train_csc
    return songs_popularity
    with open(os.path.join("IntermediateComputations", "dic_pop.pkl_no_rem"), 'rb') as handle:
        to_ret = pickle.load(handle)
    return to_ret
    # all_train, train, test, tracks, target_playlist, all_playlist_to_predict, test_songs_per_playlist, validation = get_data()
    # scores = all_train.groupby('track_id').count()
    # scores.columns = ['scores']
    # to_ret = scores.to_dict()['scores']
    # with open(os.path.join("IntermediateComputations", "dic_pop.pkl_no_rem"), 'wb') as handle:
    #     pickle.dump(to_ret, handle, protocol=pickle.HIGHEST_PROTOCOL)
    # return


def fill_URM_with_reccomendations(URM, target_recommendations):
    URM_lil = URM.tolil()
    for recommendations in target_recommendations:
        URM[recommendations[0], recommendations[1][:5]] = 1
        print(recommendations[0])
    return csr_matrix(URM_lil)


def playlist_popularity(playlist_songs, pop_dict):
    pop = 0
    count = 0
    for track in playlist_songs:
        pop += pop_dict[track]
        count += 1

    if count == 0:
        return 0

    return pop / count


def get_UCM_matrix_album(train):
    try:
        with open(os.path.join("Dataset", "UserCBF_albums.pkl"), 'rb') as handle:
            to_ret = pickle.load(handle)
            return to_ret
    except:
        _, train, _, tracks, _, _, _, _ = get_data()
        tracks_for_playlist = train.merge(tracks, on="track_id").loc[:, 'playlist_id':'album_id'].sort_values(
            by="playlist_id")
        playlists_arr = tracks_for_playlist.playlist_id.unique()
        album_arr = tracks.album_id.unique()
        UCM_albums = np.ndarray(shape=(playlists_arr.shape[0], album_arr.shape[0]))

        def create_feature_artists(entry):
            UCM_albums[entry.playlist_id][entry.album_id] = 1

        tracks_for_playlist.apply(create_feature_artists, axis=1)
        with open(os.path.join("Dataset", "UserCBF_albums.pkl"), 'wb') as handle:
            pickle.dump(UCM_albums, handle, protocol=pickle.HIGHEST_PROTOCOL)

        return UCM_albums


def get_UCM_matrix_artists(train):
    try:
        with open(os.path.join("Dataset", "UserCBF_artists.pkl"), 'rb') as handle:
            to_ret = pickle.load(handle)
            return to_ret
    except:
        _, _, _, tracks, _, _, _, _ = get_data()
        tracks_for_playlist = train.merge(tracks, on="track_id").loc[:, 'playlist_id':'artist_id'].sort_values(
            by="playlist_id")
        playlists_arr = tracks_for_playlist.playlist_id.unique()
        artists_arr = tracks.artist_id.unique()
        UCM_artists = np.ndarray(shape=(playlists_arr.shape[0], artists_arr.shape[0]))

        def create_feature_artists(entry):
            if entry.playlist_id in playlists_arr:
                UCM_artists[entry.playlist_id][entry.artist_id] += 1

        tracks_for_playlist.apply(create_feature_artists, axis=1)
        with open(os.path.join("Dataset", "UserCBF_artists.pkl"), 'wb') as handle:
            pickle.dump(UCM_artists, handle, protocol=pickle.HIGHEST_PROTOCOL)

        return UCM_artists


def get_tfidf(matrix):
    transformer = TfidfTransformer(smooth_idf=False)
    tfidf = transformer.fit_transform(matrix)
    return csr_matrix(tfidf.toarray())


def tfidf(matrix):
    transformer = TfidfTransformer(smooth_idf=False)
    tfidf = transformer.fit_transform(matrix)
    return tfidf


def lenght_playlist(playlist_songs):
    return len(playlist_songs)


def get_data():
    train = pd.read_csv(os.path.join("Dataset", "train.csv"))
    all_playlist_to_predict = pd.DataFrame(index=train.playlist_id.unique())
    s = train.playlist_id.unique()
    tracks = pd.read_csv(os.path.join("Dataset", "tracks.csv"))
    target_playlist = pd.read_csv(os.path.join("Dataset", "target_playlists.csv"))
    all_train = train.copy()
    train, test = divide_train_test(train, threshold=0.85)
    train, validation = divide_train_test(train, threshold=0.85)
    test_songs_per_playlist = make_series(test)
    all_playlist_to_predict['playlist_id'] = pd.Series(range(len(all_playlist_to_predict.index)),
                                                       index=all_playlist_to_predict.index)
    return all_train, train, test, tracks, target_playlist, all_playlist_to_predict, test_songs_per_playlist, validation


def precision(recommended_items, relevant_items):
    is_relevant = np.in1d(recommended_items, relevant_items, assume_unique=True)

    precision_score = np.sum(is_relevant, dtype=np.float32) / len(is_relevant)

    return precision_score


def recall(recommended_items, relevant_items):
    is_relevant = np.in1d(recommended_items, relevant_items, assume_unique=True)

    recall_score = np.sum(is_relevant, dtype=np.float32) / relevant_items.shape[0]

    return recall_score


def MAP(recommended_items, relevant_items):
    is_relevant = np.in1d(recommended_items, relevant_items, assume_unique=True)

    # Cumulative sum: precision at 1, at 2, at 3 ...
    # noinspection PyUnresolvedReferences
    p_at_k = is_relevant * np.cumsum(is_relevant, dtype=np.float32) / (1 + np.arange(is_relevant.shape[0]))

    # noinspection PyUnresolvedReferences
    map_score = np.sum(p_at_k) / np.min([relevant_items.shape[0], is_relevant.shape[0]])

    return map_score


# all_playlist_to_predict must be the same as the submission version, just with the recommendations for all playlist
# test_songs_per_playlist could be untouched from the beginning
def evaluate_algorithm(all_playlist_to_predict, test_songs_per_playlist, users_number=50445):
    if 'playlist_id' in all_playlist_to_predict.columns:
        tmp = all_playlist_to_predict.copy()
        tmp.set_index('playlist_id', inplace=True)
        train_series = tmp.ix[:, 0]

    else:
        train_series = all_playlist_to_predict.ix[:, 0]

    cumulative_precision = 0.0
    cumulative_recall = 0.0
    cumulative_MAP = 0.0

    num_eval = 0

    for user_id in range(users_number + 1):
        if user_id in test_songs_per_playlist.index:
            relevant_items = np.asarray(test_songs_per_playlist[user_id])

            recommended_items = train_series[user_id]
            # recommended_items = [int(x) for x in recommended_items.split(" ")]
            recommended_items = np.asarray(recommended_items)
            num_eval += 1

            cumulative_precision += precision(recommended_items, relevant_items)
            cumulative_recall += recall(recommended_items, relevant_items)
            cumulative_MAP += MAP(recommended_items, relevant_items)

    cumulative_precision /= num_eval
    cumulative_recall /= num_eval
    cumulative_MAP /= num_eval

    to_print = "Recommender performance is: Precision = {:.6f}, Recall = {:.6f}, MAP = {:.6f}".format(
        cumulative_precision, cumulative_recall, cumulative_MAP)
    print(to_print)
    return to_print


def create_URM_matrix(train):
    row = list(train.playlist_id)
    col = list(train.track_id)
    return csr_matrix(([1] * len(row), (row, col)), shape=(50446, 20635))

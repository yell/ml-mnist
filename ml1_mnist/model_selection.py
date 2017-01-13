import os.path
import numpy as np
import numpy.ma as ma
from itertools import product

from utils import RNG
from metrics import zero_one_loss


class TrainTestSplitter(object):
    """
    A generic class for splitting data into (random) subsets.

    Parameters
    ----------
    shuffle : bool, optional
        Whether to shuffle the data.
    random_seed : None or int, optional
        Pseudo-random number generator seed used for random sampling.

    Examples
    --------
    >>> import numpy as np
    >>> y = np.array([1, 1, 2, 2, 3, 3, 3])

    >>> tts1 = TrainTestSplitter(shuffle=False)
    >>> train, test = tts1.split(y, train_ratio=0.5)
    >>> print y[train], y[test]
    [1 1 2] [2 3 3 3]
    >>> train, test = tts1.split(y, train_ratio=0.5, stratify=True)
    >>> print y[train], y[test]
    [1 2 3] [1 2 3 3]
    >>> for fold in tts1.make_k_folds(y, n_folds=3):
    ...     print y[fold]
    [1 1 2]
    [2 3]
    [3 3]
    >>> for fold in tts1.make_k_folds(y, n_folds=3, stratify=True):
    ...     print y[fold]
    [1 2 3]
    [1 2 3]
    [3]
    >>> for train, test in tts1.k_fold_split(y, n_folds=3):
    ...     print y[train], y[test]
    [2 3 3 3] [1 1 2]
    [1 1 2 3 3] [2 3]
    [1 1 2 2 3] [3 3]
    >>> for train, test in tts1.k_fold_split(y, n_folds=3, stratify=True):
    ...     print y[train], y[test]
    [1 2 3 3] [1 2 3]
    [1 2 3 3] [1 2 3]
    [1 2 3 1 2 3] [3]

    >>> tts2 = TrainTestSplitter(shuffle=True, random_seed=1337)
    >>> train, test = tts2.split(y, train_ratio=0.5)
    >>> print y[train], y[test]
    [3 2 1] [2 1 3 3]
    >>> train, test = tts2.split(y, train_ratio=0.5, stratify=True)
    >>> print y[train], y[test]
    [3 1 2] [3 3 2 1]
    >>> for fold in tts2.make_k_folds(y, n_folds=3):
    ...     print y[fold]
    [3 2 1]
    [2 1]
    [3 3]
    >>> for fold in tts2.make_k_folds(y, n_folds=3, stratify=True):
    ...     print y[fold]
    [3 1 2]
    [3 2 1]
    [3]
    """
    def __init__(self, shuffle=False, random_seed=None):
        self.shuffle = shuffle
        self.random_seed = random_seed
        self.rng = RNG(self.random_seed)

    def split(self, y, train_ratio=0.8, stratify=False):
        """
        Split data into train and test subsets.

        Parameters
        ----------
        y : (n_samples,) array-like
            The target variable for supervised learning problems.
        train_ratio : float, 0 < `train_ratio` < 1, optional
            the proportion of the dataset to include in the train split.
        stratify : bool, optional
            If True, the folds are made by preserving the percentage of samples
            for each class. Stratification is done based upon the `y` labels.

        Returns
        -------
        train : (n_train,) np.ndarray
            The training set indices for that split.
        test : (n_samples - n_train,) np.ndarray
            The testing set indices for that split.
        """
        self.rng.reseed()
        n = len(y)

        if not stratify:
            indices = self.rng.permutation(n) if self.shuffle else np.arange(n, dtype=np.int)
            train_size = int(train_ratio * n)
            return np.split(indices, (train_size,))

        # group indices by label
        labels_indices = {}
        for index, label in enumerate(y):
            if not label in labels_indices: labels_indices[label] = []
            labels_indices[label].append(index)

        train, test = np.array([], dtype=np.int), np.array([], dtype=np.int)
        for label, indices in sorted(labels_indices.items()):
            size = int(train_ratio * len(indices))
            train = np.concatenate((train, indices[:size]))
            test  = np.concatenate(( test, indices[size:]))

        if self.shuffle:
            self.rng.shuffle(train)
            self.rng.shuffle(test)

        return train, test

    def make_k_folds(self, y, n_folds=3, stratify=False):
        """
        Split data into folds of (approximately) equal size.

        Parameters
        ----------
        y : (n_samples,) array-like
            The target variable for supervised learning problems.
            Stratification is done based upon the `y` labels.
        n_folds : int, `n_folds` > 1, optional
            Number of folds.
        stratify : bool, optional
            If True, the folds are made by preserving the percentage of samples
            for each class. Stratification is done based upon the `y` labels.

        Yields
        ------
        fold : np.ndarray
            Indices for current fold.
        """
        self.rng.reseed()
        n = len(y)

        if not stratify:
            indices = self.rng.permutation(n) if self.shuffle else np.arange(n, dtype=np.int)
            for fold in np.array_split(indices, n_folds):
                yield fold
            return

        # group indices
        labels_indices = {}
        for index, label in enumerate(y):
            if not label in labels_indices:
                labels_indices[label] = []
            labels_indices[label].append(index)

        # split all indices label-wisely
        for label, indices in sorted(labels_indices.items()):
            labels_indices[label] = np.array_split(indices, n_folds)

        # collect respective splits into folds and shuffle if needed
        for k in xrange(n_folds):
            fold = np.concatenate([indices[k] for _, indices in sorted(labels_indices.items())])
            if self.shuffle:
                self.rng.shuffle(fold)
            yield fold

    def k_fold_split(self, y, n_splits=3, stratify=False):
        """
        Split data into train and test subsets for K-fold CV.

        Parameters
        ----------
        y : (n_samples,) array-like
            The target variable for supervised learning problems.
            Stratification is done based upon the `y` labels.
        n_splits : int, `n_splits` > 1, optional
            Number of folds.
        stratify : bool, optional
            If True, the folds are made by preserving the percentage of samples
            for each class. Stratification is done based upon the `y` labels.

        Yields
        ------
        train : (n_train,) np.ndarray
            The training set indices for current split.
        test : (n_samples - n_train,) np.ndarray
            The testing set indices for current split.
        """
        folds = list(self.make_k_folds(y, n_folds=n_splits, stratify=stratify))
        for i in xrange(n_splits):
            yield np.concatenate(folds[:i] + folds[(i + 1):]), folds[i]


class GridSearchCV(object):
    """Exhaustive search over specified parameter values for a `model`.

    Parameters
    ----------
    model : model object
        This is assumed to implement the ml1_mnist.BaseEstimator interface.
    param_grid : dict[str] = iterable, or iterable of such
        Dictionary with parameters possible values or an iterable (e.g. list)
        of such dictionaries, in which case the grids spanned by each dictionary
        in the list are explored. This enables searching over any sequence
        of parameter settings. The rest of the parameter are default one.
    param_order : {None, [str]} or iterable of such, optional
        List of parameter names specifying the order by which parameters in grid
        are explored. The smaller index of parameter in this list, the outer, so
        to say, for-loop he participates in. If multiple grids are specified,
        multiple lists (or None) are expected. If None, parameters are explored in
        sorted order (for each grid separately, if multiple of them are provided).
    train_test_splitter_params : kwargs, optional
        Params passed to `TrainTestSplitter`.
    n_splits : int, optional
        Number of folds passed to `TrainTestSplitter.k_fold_split`.
    refit : bool, optional
        If False, refit model only for new combination of X, y (and not on
        new combinations of parameters). It may be reasonable choice for
        non-parametric models, such models as KNNClassifier, for instance.
    save_models : bool, optional
        If True, save new best models to `dirpath`.
    dirpath : str, optional
        Where to save models if `save_models` set to True.
    save_params : kwargs, optional
        Additional params that are passed to `model.save`
    TODO: verbose : bool, optional
        If True, print the results of each iteration.

    Attributes
    ----------
    cv_results_ : dict[str] = np.ndarray | np.ma.ndarray
        Can be imported into a pandas.DataFrame
    best_model_ : model object
        Model that was chosen by the search, i.e. which gave smallest loss.
    best_loss_ : float
        Loss of `best_model_` on the left out data.
    best_params_ : dict
        Parameter setting that gave the best results on the hold out data.
    best_index_ : int
        The index (of the `cv_results_` arrays) which corresponds to the best
        candidate parameter setting.

    Examples
    --------
    >>> from knn import KNNClassifier
    >>> param_grid = ({'weights': ['uniform', 'distance'],
    ...                'p': [1., 2., np.inf],
    ...                'k': [2, 3, 4]},
    ...               {'kernel': ['rbf', 'poly'],
    ...                'k': [2, 3],
    ...                'gamma': [0.01, 0.1]})
    >>> param_order = (['weights', 'p'],
    ...                None)
    >>> grid_cv = GridSearchCV(model=KNNClassifier(), param_grid=param_grid, param_order=param_order)
    >>> for params in grid_cv.gen_params():
    ...     print params # note the order
    {'p': 1.0, 'k': 2, 'weights': 'uniform'}
    {'p': 1.0, 'k': 3, 'weights': 'uniform'}
    {'p': 1.0, 'k': 4, 'weights': 'uniform'}
    {'p': 2.0, 'k': 2, 'weights': 'uniform'}
    {'p': 2.0, 'k': 3, 'weights': 'uniform'}
    {'p': 2.0, 'k': 4, 'weights': 'uniform'}
    {'p': inf, 'k': 2, 'weights': 'uniform'}
    {'p': inf, 'k': 3, 'weights': 'uniform'}
    {'p': inf, 'k': 4, 'weights': 'uniform'}
    {'p': 1.0, 'k': 2, 'weights': 'distance'}
    {'p': 1.0, 'k': 3, 'weights': 'distance'}
    {'p': 1.0, 'k': 4, 'weights': 'distance'}
    {'p': 2.0, 'k': 2, 'weights': 'distance'}
    {'p': 2.0, 'k': 3, 'weights': 'distance'}
    {'p': 2.0, 'k': 4, 'weights': 'distance'}
    {'p': inf, 'k': 2, 'weights': 'distance'}
    {'p': inf, 'k': 3, 'weights': 'distance'}
    {'p': inf, 'k': 4, 'weights': 'distance'}
    {'kernel': 'rbf', 'k': 2, 'gamma': 0.01}
    {'kernel': 'poly', 'k': 2, 'gamma': 0.01}
    {'kernel': 'rbf', 'k': 3, 'gamma': 0.01}
    {'kernel': 'poly', 'k': 3, 'gamma': 0.01}
    {'kernel': 'rbf', 'k': 2, 'gamma': 0.1}
    {'kernel': 'poly', 'k': 2, 'gamma': 0.1}
    {'kernel': 'rbf', 'k': 3, 'gamma': 0.1}
    {'kernel': 'poly', 'k': 3, 'gamma': 0.1}
    >>> grid_cv.unique_params()
    ['gamma', 'k', 'kernel', 'p', 'weights']
    >>> X = [[0., 0.], [0., 1.], [1., 0.], [1., 1.],
    ...      [0.9, 0.99], [0.1, 0.25], [0.8, 0.2], [0.45, 0.55]]
    >>> y = [0, 1, 1, 0, 0, 0, 1, 1]
    >>> param_grid = ({'weights': ['uniform', 'distance'], 'k': [2, 3]}, {'p': [1., np.inf], 'k': [2]})

    >>> grid_cv = GridSearchCV(model=KNNClassifier(), param_grid=param_grid, n_splits=2,
    ...                        refit=False, save_models=False ,verbose=False)
    >>> grid_cv.fit(X, y) # doctest: +ELLIPSIS
    <model_selection.GridSearchCV object at 0x...>
    >>> grid_cv.best_loss_
    0.0
    >>> grid_cv.best_params_
    {'k': 2, 'weights': 'distance'}
    >>> for k, v in sorted(grid_cv.cv_results_.items()):
    ...     print k, ":", " ".join(map(str, v)) # doctest: +ELLIPSIS
    mean_loss : 0.25 0.0 0.625 0.125 0.375 0.25
    param_k : 2.0 2.0 3.0 3.0 2.0 2.0
    param_p : -- -- -- -- 1.0 inf
    param_weights : uniform distance uniform distance -- --
    params : {'k': 2, 'weights': 'uniform'} {'k': 2, 'weights': 'distance'} {...} {...} {...} {...}
    split0_loss : 0.25 0.0 0.75 0.0 0.5 0.25
    split1_loss : 0.25 0.0 0.5 0.25 0.25 0.25
    std_loss : 0.0 0.0 0.125 0.125 0.125 0.0
    """
    def __init__(self, model, param_grid, param_order=None, train_test_splitter_params={},
                 n_splits=3, loss=zero_one_loss, refit=True, save_models=True, dirpath='.', save_params={},
                 verbose=True):

        self.model = model

        self.param_grid = param_grid
        if isinstance(self.param_grid, dict):
            self.param_grid = (self.param_grid,)

        self.param_order = param_order
        if not self.param_order:
            self.param_order = [self.param_order] * len(self.param_grid)

        self.train_test_splitter_params = train_test_splitter_params
        self.n_splits = n_splits
        self.loss = loss
        self.refit = refit
        self.save_models = save_models
        self.dirpath = dirpath
        self.save_params = save_params
        self.verbose = verbose

        self.cv_results_ = {}
        self.best_model_ = self.model
        self.best_loss_ = np.inf
        self.best_params_ = None
        self.best_index_ = None

    def unique_params(self):
        unique = set()
        for grid in self.param_grid:
            unique |= set(grid.keys())
        return list(sorted(unique))

    def gen_params(self):
        """Generate all possible combinations of params.

        Yields
        ------
        params : dict
            Current parameters for model.
        """
        # convert to zip-lists and use itertools' magic
        for i, grid in enumerate(self.param_grid):
            zip_lists = []
            order = self.param_order[i]
            for param_name in sorted(grid, key=lambda x: order.index(x) if (order and x in order) else x):
                param_values = grid[param_name]
                zip_lists.append([(param_name, v) for v in param_values])
            for combination in product(*zip_lists):
                yield dict(combination)

    def _check_X_y(self, X, y):
        if not isinstance(X, np.ndarray):
            X = np.asarray(X)
        if not isinstance(y, np.ndarray):
            y = np.asarray(y)
        return X, y

    def _best_model_name(self):
        name = self.best_model_.model_name()
        name += "__loss_"
        name += "{0:.5f}".format(self.best_loss_).replace('.', '_')
        for k, v in sorted(self.best_params_.items()):
            name += "__"
            name += str(k)
            name += "_"
            name += str(v)
        name += ".json"
        return name

    def fit(self, X, y):
        X, y = self._check_X_y(X, y)
        unique_params = self.unique_params()
        tts = TrainTestSplitter(**self.train_test_splitter_params)

        # initialize `cv_results_`
        self.cv_results_['mean_loss'] = []
        self.cv_results_['std_loss'] = []
        self.cv_results_['params'] = []
        for k in xrange(self.n_splits):
            self.cv_results_['split{0}_loss'.format(k)] = []
        for param_name in unique_params:
            self.cv_results_['param_{0}'.format(param_name)] = ma.array([])

        if self.refit:
            # for each param combination fit consequently on each fold
            # to obtain mean loss across splits as soon as possible
            for params_index, params in enumerate(self.gen_params()):

                # set params and add to `cv_results_`
                self.model.reset_params().set_params(**params)
                self.cv_results_['params'].append(params)

                for param_name in unique_params:
                    cv_key = 'param_{0}'.format(param_name)
                    mask = [int(not param_name in params)]
                    to_concat = ma.array([params.get(param_name, None)], mask=mask)
                    self.cv_results_[cv_key] = ma.concatenate((self.cv_results_[cv_key],
                                                               to_concat))
                splits_losses = []
                for split_index, (train, test) in enumerate(tts.k_fold_split(y, n_splits=self.n_splits,
                                                                            stratify=True)):
                    # fit and evaluate
                    y_pred = self.model.fit(X[train], y[train]).predict(X[test])
                    loss = self.loss(y[test], y_pred)
                    splits_losses.append(loss)
                    # add loss to `cv_results_`
                    cv_key = 'split{0}_loss'.format(split_index)
                    self.cv_results_[cv_key].append(loss)

                # compute mean and std loss
                splits_losses = np.asarray(splits_losses)
                mean_loss = np.mean(splits_losses)
                std_loss = np.std(splits_losses)
                self.cv_results_['mean_loss'].append(mean_loss)
                self.cv_results_['std_loss'].append(std_loss)
                # update 'best' attributes
                if mean_loss < self.best_loss_:
                    self.best_index_ = params_index
                    self.best_loss_ = mean_loss
                    self.best_params_ = params
                    self.best_model_ = self.model
                    if self.save_models:
                        self.best_model_.save(filepath=os.path.join(self.dirpath, self._best_model_name()),
                                              **self.save_params)
        else: # if self.refit == False
            # fit for each fold and then evaluate on each combination
            # of params
            for split_index, (train, test) in enumerate(tts.k_fold_split(y, n_splits=self.n_splits,
                                                                         stratify=True)):
                # fit model
                self.model.fit(X[train], y[train])

                for params_index, params in enumerate(self.gen_params()):
                    # set params
                    self.model.reset_params().set_params(**params)
                    # on first split add params to `cv_results_`
                    if split_index == 0:
                        self.cv_results_['params'].append(params)
                        for param_name in unique_params:
                            cv_key = 'param_{0}'.format(param_name)
                            mask = [int(not param_name in params)]
                            to_concat = ma.array([params.get(param_name, None)], mask=mask)
                            self.cv_results_[cv_key] = ma.concatenate((self.cv_results_[cv_key],
                                                                       to_concat))
                    # evaluate
                    y_pred = self.model.predict(X[test])
                    loss = self.loss(y[test], y_pred)
                    # add loss to `cv_results_`
                    cv_key = 'split{0}_loss'.format(split_index)
                    self.cv_results_[cv_key].append(loss)
                    # after last split ...
                    if split_index == self.n_splits - 1:
                        # ... compute means, stds
                        splits_losses = [self.cv_results_['split{0}_loss'.format(k)][params_index]
                                         for k in xrange(self.n_splits)]
                        mean_loss = np.mean(splits_losses)
                        std_loss = np.std(splits_losses)
                        self.cv_results_['mean_loss'].append(mean_loss)
                        self.cv_results_['std_loss'].append(std_loss)
                        # ... and update best attributes
                        if mean_loss < self.best_loss_:
                            self.best_index_ = params_index
                            self.best_loss_ = mean_loss
                            self.best_params_ = params
                            self.best_model_ = self.model
                            self.best_model_.save(filepath=os.path.join(self.dirpath, self._best_model_name()),
                                                  **self.save_params)
        # convert lists to np.ndarray
        for key in (['mean_loss', 'std_loss', 'params'] +
                    ['split{0}_loss'.format(k) for k in xrange(self.n_splits)]):
            self.cv_results_[key] = np.asarray(self.cv_results_[key])
        return self

    def to_df(self):
        pass


if __name__ == '__main__':
    # run corresponding tests
    import test_model_selection as t
    from utils.testing import run_tests
    run_tests(__file__, t)
    # from knn import KNNClassifier
    # X = [[0., 0.], [0., 1.], [1., 0.], [1., 1.],
    #      [0.9, 0.99], [0.1, 0.25], [0.8, 0.2], [0.45, 0.55]]
    # y = [0, 1, 1, 0, 0, 0, 1, 1]
    # param_grid = ({'weights': ['uniform', 'distance'], 'k': [2, 3]}, {'p': [1., np.inf], 'k': [2]})
    # grid_cv = GridSearchCV(model=KNNClassifier(), param_grid=param_grid, n_splits=2,
    #                        refit = False, save_models = True, dirpath = '../cv_results/', verbose = False)
    # grid_cv.fit(X, y)
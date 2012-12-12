"""
Epac : Embarrassingly Parallel Array Computing
"""
print __doc__


import numpy as np


## ==================== ##
## == Stores and I/O == ##
## ==================== ##

class Store(object):
    """Abstract Store"""

    def __init__(self):
        pass

    def save_map_output(key1, key2=None, val2=None, keyvals2=None):
        pass


class StoreLo(Store):
    """ Store based on Living Objects"""

    def __init__(self, storage_root):
        pass

    def save_map_output(self, key1, key2=None, val2=None, keyvals2=None):
        pass


class StoreFs(Store):
    """ Store based of file system"""

    def __init__(self):
        pass

    def key2path(self, key):
        prot, path = key_split(key)
        import os
        if not os.path.exists(path):
            os.makedirs(path)
        return path

    def save_map_output(self, key1, key2=None, val2=None, keyvals2=None):
        path = self.key2path(key1)
        import os
        if key2 and val2:
            keyvals2 = dict()
            keyvals2[key2] = val2
        for key2 in keyvals2.keys():
            val2 = keyvals2[key2]
            filename = Config.store_fs_map_output_prefix + key2 +\
                Config.store_fs_pickle_suffix
            file_path = os.path.join(path, filename)
            self.save_pickle(val2, file_path)

    def save_object(self, obj, key):
        path = self.key2path(key)
        import os
        class_name = str(obj.__class__).split(".")[-1].\
            replace(r"'", "").replace(r">", "")
        # try to save in json format
        filename = Config.store_fs_node_prefix + class_name +\
            Config.store_fs_json_suffix
        file_path = os.path.join(path, filename)
        if self.save_json(obj, file_path):
            # saving in json failed => pickle
            filename = Config.store_fs_node_prefix + class_name +\
            Config.store_fs_pickle_suffix
            file_path = os.path.join(path, filename)
            self.save_pickle(obj, file_path)

    def load_object(self, key):
        """Load a node given a key, recursive=True recursively walk through
        children"""
        path = self.key2path(key)
        import os
        prefix = os.path.join(path, Config.store_fs_node_prefix)
        import glob
        file_path = glob.glob(prefix + '*')
        if len(file_path) != 1:
            raise IOError('Found no or more that one file in %s' % (prefix))
        file_path = file_path[0]
        _, ext = os.path.splitext(file_path)
        if ext == Config.store_fs_json_suffix:
            obj_dict = self.load_json(file_path)
            class_str = file_path.replace(prefix, "").\
                replace(Config.store_fs_json_suffix, "")
            obj = object.__new__(eval(class_str))
            obj.__dict__.update(obj_dict)
        elif ext == Config.store_fs_pickle_suffix:
            obj = self.load_pickle(file_path)
        else:
            raise IOError('File %s has an unkown extension: %s' %
                (file_path, ext))
        return obj

    def load_map_output(self, key):
        path = self.key2path(key)
        import os
        import glob
        map_paths = glob.glob(os.path.join(path,
            Config.store_fs_map_output_prefix) + '*')
        map_outputs = dict()
        for map_path in map_paths:
            ext = os.path.splitext(map_path)[-1]
            if ext == Config.store_fs_pickle_suffix:
                map_obj = self.load_pickle(map_path)
            if ext == Config.store_fs_json_suffix:
                map_obj = self.load_json(map_path)
            key = os.path.splitext(os.path.basename(map_path))[0].\
                replace(Config.store_fs_map_output_prefix, "", 1)
            map_outputs[key] = map_obj
        return map_outputs

    def save_pickle(self, obj, file_path):
            import pickle
            output = open(file_path, 'wb')
            pickle.dump(obj, output)
            output.close()

    def load_pickle(self, file_path):
            #u'/tmp/store/KFold-0/SVC/__node__NodeEstimator.pkl'
            import pickle
            inputf = open(file_path, 'rb')
            obj = pickle.load(inputf)
            inputf.close()
            return obj

    def save_json(self, obj, file_path):
            import json
            import os
            output = open(file_path, 'wb')
            try:
                json.dump(obj.__dict__, output)
            except TypeError:  # save in pickle
                output.close()
                os.remove(file_path)
                return 1
            output.close()
            return 0

    def load_json(self, file_path):
            import json
            inputf = open(file_path, 'rb')
            obj = json.load(inputf)
            inputf.close()
            return obj


def get_store(key):
    """ factory function returning the Store object of the class
    associated with the key parameter"""
    prot, path = key_split(key)
    if prot == Config.key_prot_fs:
        return StoreFs()
    elif prot == Config.key_prot_lo:
        return StoreLo(storage_root=Node.roots[path])
    else:
        raise ValueError("Invalid value for key: should be:" +\
        "lo for no persistence and storage on living objects or" +\
        "fs and a directory path for file system based storage")


def key_split(key):
    return key.split(Config.key_prot_path_sep, 1)


def key_join(prot="", path=""):
    return prot + Config.key_prot_path_sep + path


def key_pop(key):
    import os
    return os.path.dirname(key)


def key_push(key, basename):
    return key + Config.key_path_sep + basename


def save_map_output(key1, key2=None, val2=None, keyvals2=None):
    store = get_store(key1)
    store.save_map_output(key1, key2, val2, keyvals2)


class Config:
    store_fs_pickle_suffix = ".pkl"
    store_fs_json_suffix = ".json"
    store_fs_map_output_prefix = "__map__"
    store_fs_node_prefix = "__node__"
    key_prot_lo = "mem"  # key storage protocol: living object
    key_prot_fs = "file"  # key storage protocol: file system
    key_path_sep = "/"
    key_prot_path_sep = "://"  # key storage protocol / path separator
    kwargs_data_prefix = ["X", "y"]
    recursive_up = 1
    recursive_down = 2


class Node(object):
    """Parallelization node, provide:
        - key/val
        - I/O interface with the store."""

    def __init__(self, steps=None, key=None, store=None, **kwargs):
        self.__dict__.update(kwargs)
        self.parent = None
        self.children = list()
        self.map_outputs = dict()
        # If a steps is provided: initial construction of the execution tree
        if steps:
            if not store:
                import string
                import random
                self.name = key_join(prot=Config.key_prot_lo,
                    path="".join(random.choice(string.ascii_uppercase +
                        string.digits) for x in range(10)))
                self.build_tree(steps, **kwargs)
            # store is a string and a valid directory , assume that storage
            # will be done on the file system, ie.: key prefix "fs://"
            elif isinstance(store, str):
                self.name = key_join(prot=Config.key_prot_fs,
                                     path=store)
                self.build_tree(steps, **kwargs)
                self.save_node()
            else:
                raise ValueError("Invalid value for store: should be: " +\
                "None for no persistence and storage on living objects or " +\
                "a string path for file system based storage")
        # If not steps but store or key : load from fs store
        if not steps and (isinstance(store, str) or isinstance(key, str)):
            root = load_node(key=key, store=store)
            self.__dict__.update(root.__dict__)

    # --------------------- #
    # -- Tree operations -- #
    # --------------------- #

    def add_child(self, child):
        self.children.append(child)
        child.parent = self

    def add_children(self, children):
        for child in children:
            self.add_child(child)

    def get_name(self):
        return self.name

    def get_key(self):
        if not self.parent:
            return self.get_name()
        return key_push(self.parent.get_key(), self.get_name())

    def get_leaves(self):
        if not len(self.children):
            return [self]
        else:
            leaves = []
            for child in self.children:
                leaves = leaves + child.get_leaves()
            return leaves

    def get_path_from_root(self):
        if self.parent is None:
            return [self]
        return self.parent.get_path_from_root() + [self]

    def build_tree(self, steps, **kwargs):
        """Build execution tree.

        Parameters
        ----------
        steps: list
        """
        if len(steps) == 0:
            return
        # If current step is a Parallelization node: a foactory of ParNode
        if isinstance(steps[0], Splitter):
            for child in steps[0].produceNodes():
                self.add_children(child)
                child.build_tree(steps[1:], **kwargs)
        else:
            import copy
            child = copy.deepcopy(steps[0])
            self.add_children(child)
            child.build_tree(steps[1:], **kwargs)

    def __iter__(self):
        """ Iterate over leaves"""
        for leaf in self.get_leaves():
            yield leaf

    def add_map_output(self, key=None, val=None, keyvals=None):
        """ Collect map output

        Parameters
        ----------
        key : (string) the intermediary key
        val : (dictionary, list, tuple or array) the intermediary value
        produced by the mapper.
                If key/val are provided a single map output is added

        keyvals : a dictionary of intermediary keys/values produced by the
        mapper.
        """
        if key and val:
            self.map_outputs[key] = val
        if keyvals:
            self.map_outputs.update(keyvals)

    # ------------------------------------------ #
    # -- Top-down data-flow operations (map)  -- #
    # ------------------------------------------ #

    def topdown(self, recursive=True, **kwargs):
        """Top-down data processing method

            This method does nothing more that recursively call
            parent/children map. Most of time, it should be re-defined.

            Parameters
            ----------
            recursive: boolean
                if True recursively call parent/children map. If the
                current node is the root of the tree call the children.
                This way the whole tree is executed.
                If it is a leaf, then recursively call the parent before
                being executed. This a pipeline made of the path from the
                leaf to the root is executed.
            **kwargs: dict
                the keyword dictionnary of data flow

            Return
            ------
            A dictionnary of processed data
        """
        print "topdown", self.get_key()
        recursive = self.check_recursive(recursive)
        if recursive is Config.recursive_up:
            # Recursively call parent map up to root
            kwargs = self.parent.topdown(recursive=recursive, **kwargs)
        kwargs = self.transform(**kwargs)
        if recursive is Config.recursive_down:
            # Call children map down to leaves
            [child.topdown(recursive=recursive, **kwargs) for child
                in self.children]
        return kwargs

    def transform(self, **kwargs):
        return kwargs

    def check_recursive(self, recursive):
        if recursive and type(recursive) is bool:
            if not self.children:
                recursive = Config.recursive_up
            elif not self.parent:
                recursive = Config.recursive_down
            else:
                raise ValueError("recursive is True, but the node is neither"+\
            "a leaf or the root tree, it then not possible to guess"+ \
            "if recurssion should go up or down")
        if recursive is Config.recursive_up and not self.parent:
            recursive = False
        elif recursive is Config.recursive_down and not self.children:
            recursive = False
        return recursive

    # --------------------------------------------- #
    # -- Bottum-up data-flow operations (reduce) -- #
    # --------------------------------------------- #

    def reduce(self):
        # Terminaison (leaf) node
        if len(self.children) == 0:
            return self.map_outputs
        # 1) Build sub-aggregates over children
        sub_aggregates = [child.reduce() for child in self.children]
        # 2) Agregate children's sub-aggregates
        aggregate = dict()
        for sub_aggregate in sub_aggregates:
            #sub_aggregate = sub_aggregates[0]
            for key2 in sub_aggregate.keys():
                #key2 = sub_aggregate.keys()[0]
                map_out = sub_aggregate[key2]
                # map_out is a dictionary
                if isinstance(map_out, dict):
                    if not key2 in aggregate.keys():
                        aggregate[key2] = dict()
                    for key3 in map_out.keys():
                        if not key3 in aggregate[key2].keys():
                            aggregate[key2][key3] = list()
                        aggregate[key2][key3].append(map_out[key3])
                else:  # simply concatenate
                    if not key2 in aggregate.keys():
                        aggregate[key2] = list()
                    aggregate[key2].append(map_out)
        return aggregate

    # -------------------------------- #
    # -- I/O persistance operations -- #
    # -------------------------------- #

    def save_node(self, recursive=True):
        """I/O (persistance) operation: save the node on the store"""
        key = self.get_key()
        store = get_store(key)
        # Prevent recursive saving of children/parent in a single dump:
        # replace reference to chidren/parent by basename strings
        import copy
        clone = copy.copy(self)
        clone.children = [child.name for child in self.children]
        if self.parent:
            clone.parent = ".."
        store.save_object(clone, key)
        recursive = self.check_recursive(recursive)
        if recursive is Config.recursive_up:
            # Recursively call parent save up to root
            self.parent.save_node(recursive=recursive)
        if recursive is Config.recursive_down:
            # Call children save down to leaves
            [child.save_node(recursive=recursive) for child
                in self.children]


def load_node(key=None, store=None, recursive=True):
    """I/O (persistance) operation load a node from the store"""
    if key is None:
        key = key_join(prot=Config.key_prot_fs, path=store)
    #self.add_children(self.build_execution_tree(steps, data))
    store = get_store(key)
    node = store.load_object(key)
    # children contain basename string: Save the string a Recursively
    # walk/load children
    recursive = node.check_recursive(recursive)
    if recursive is Config.recursive_up:
        parent_key = key_pop(key)
        parent = load_node(key=parent_key, recursive=recursive)
        parent.add_child(node)
    if recursive is Config.recursive_down:
        children = node.children
        node.children = list()
        for child in children:
            child_key = key_push(key, child)
            node.add_child(load_node(key=child_key, recursive=recursive))
    return node

## ================================= ##
## == Wrapper node for estimators == ##
## ================================= ##

class NodeEstimator(Node):
    """Node that wrap estimators"""

    def __init__(self, estimator, **kwargs):
        self.estimator = estimator
        super(NodeEstimator, self).__init__(
            name=estimator.__class__.__name__, **kwargs)

    def __repr__(self):
        return '%s(estimator=%s)' % (self.__class__.__name__,
            self.estimator.__repr__())

    def transform(self, **kwargs):
        kwargs_train, kwargs_test = NodeKFold.split_train_test(**kwargs)
        self.estimator.fit(**kwargs_train)            # fit the training data
        if self.children:                         # transform input to output
            kwargs_train["X"] = self.estimator.transform(X=kwargs_train.pop("X"))
            kwargs_test["X"] = self.estimator.transform(X=kwargs_test.pop("X"))
            kwargs = NodeKFold.join_train_test(kwargs_train, kwargs_test)
        else:                 # leaf node: do the prediction predict the test
            y_true = kwargs_test.pop("y")
            y_pred = self.estimator.predict(**kwargs_test)
            kwargs = dict(y_true=y_true, y_pred=y_pred)
            self.add_map_output(keyvals=kwargs)             # collect map output
        return kwargs

# ------------ #
# -- Helper -- #
# ------------ #

def node_factory(cls, node_kwargs):
    instance = object.__new__(cls)
    instance.__init__(**node_kwargs)
    return NodeEstimator(instance)

N = node_factory

## =========================== ##
## == Parallelization nodes == ##
## =========================== ##

class Splitter(object):
    """Abstract class for Factories of parallelization nodes that implement
    produceNodes"""

    def produceNodes(self):
        raise NotImplementedError("Cannot call abstract method")

# -------------------------------- #
# -- Generic slicing operations -- #
# -------------------------------- #
    
class NodeSlicer(Node):
    """Parallelization is based on several reslicing of the same dataset:
    Slices can be split (shards) or a resampling of the original datasets.
    """
    def __init__(self, transform_only=None, **kwargs):
        super(NodeSlicer, self).__init__(**kwargs)
        self.transform_only = transform_only


class NodeRowSlicer(NodeSlicer):
    """Parallelization is based on several row-wise reslicing of the same
    dataset

    Parameters
    ----------
    slices: dict of sets of slicing indexes or a single set of slicing indexes
    """

    def __init__(self, slices, **kwargs):
        super(NodeRowSlicer, self).__init__(**kwargs)
        # convert a as list if required
        if isinstance(slices, dict):
            self.slices =\
                {k: slices[k].tolist() if isinstance(slices[k], np.ndarray)
                else slices[k] for k in slices}
        else:
            self.slices = \
                slices.tolist() if isinstance(slices, np.ndarray) else slices

    def transform(self, **kwargs):
        keys_data = self.transform_only if self.transform_only\
                    else kwargs.keys()
        data_out = kwargs.copy()
        for key_data in keys_data:  # slice input data
            if isinstance(self.slices, dict):
                # rename output keys according to input keys and slice keys
                data = data_out.pop(key_data)
                for key_slice in self.slices:
                    data_out[key_data + key_slice] = \
                        data[self.slices[key_slice]]
            else:
                data_out[key_data] = data_out[key_data][self.slices]
        return data_out

# ----------------------- #
# -- Cross-validations -- #
# ----------------------- #

class NodeKFold(NodeRowSlicer):
    """ KFold parallelization node"""
    train_data_suffix = "train"
    test_data_suffix = "test"

    def __init__(self, n=None, n_folds=None, slices=None, nb=None, **kwargs):
        super(NodeKFold, self).__init__(slices=slices,
            name="KFold-" + str(nb), **kwargs)
        self.n = n
        self.n_folds = n_folds

    @classmethod
    def split_train_test(cls, **kwargs):
        """Split kwargs into train dict (that contains train suffix in kw)
        and test dict (that contains test suffix in kw).

        Returns
        -------
        Two dictionaries without the train and test suffix into kw. Outputs
        are then compliant with estimator API that takes only X, y paramaters.
        If only "X" an "y" kw are found they are replicated into the both
        outputs.

        Example
        -------
       >>> NodeKFold.split_train_test(Xtrain=1, ytrain=2, Xtest=-1, ytest=-2,
       ... a=33)
       ({'y': 2, 'X': 1, 'a': 33}, {'y': -2, 'X': -1, 'a': 33})

        >>> NodeKFold.split_train_test(X=1, y=2, a=33)
        ({'y': 2, 'X': 1, 'a': 33}, {'y': 2, 'X': 1, 'a': 33})
        """
        kwargs_train = kwargs.copy()
        kwargs_test = kwargs.copy()
        for data_key in Config.kwargs_data_prefix:
            data_key_train = data_key + NodeKFold.train_data_suffix
            data_key_test = data_key + NodeKFold.test_data_suffix
            if data_key_test in kwargs_train:  # Remove [X|y]test from train
                kwargs_train.pop(data_key_test)
            if data_key_train in kwargs_test:  # Remove [X|y]train from test
                kwargs_test.pop(data_key_train)
            # [X|y]train becomes [X|y] to be complient with estimator API
            if data_key_train in kwargs_train:
                kwargs_train[data_key] = kwargs_train.pop(data_key_train)
            # [X|y]test becomes [X|y] to be complient with estimator API
            if data_key_test in kwargs_test:
                kwargs_test[data_key] = kwargs_test.pop(data_key_test)
        return kwargs_train, kwargs_test

    @classmethod
    def join_train_test(cls, kwargs_train, kwargs_test):
        """Merge train test separate kwargs into single dict.

            Returns
            -------
            A single dictionary with train and test suffix as kw.

            Example
            -------
            >>> NodeKFold.join_train_test(dict(X=1, y=2, a=33),
            ...                          dict(X=-1, y=-2, a=33))
            {'ytest': -2, 'Xtest': -1, 'a': 33, 'Xtrain': 1, 'ytrain': 2}
        """
        kwargs = dict()
        for data_key in Config.kwargs_data_prefix:
            if data_key in kwargs_train:  # Get [X|y] from train
                data_key_train = data_key + NodeKFold.train_data_suffix
                kwargs[data_key_train] = kwargs_train.pop(data_key)
            if data_key in kwargs_test:  # Get [X|y] from train
                data_key_test = data_key + NodeKFold.test_data_suffix
                kwargs[data_key_test] = kwargs_test.pop(data_key)
        kwargs.update(kwargs_train)
        kwargs.update(kwargs_test)
        return kwargs

class SplitKFold(Splitter):
    """NodeKfold Factory"""

    def __init__(self, n, n_folds):
        self.n_folds = n_folds
        self.n = n

    def produceNodes(self):
        nodes = []
        from sklearn.cross_validation import KFold  # StratifiedKFold
        nb = 0
        for train, test in KFold(n=self.n, n_folds=self.n_folds):
            nodes.append(NodeKFold(slices={NodeKFold.train_data_suffix: train,
                                          NodeKFold.test_data_suffix: test},
                                          nb=nb))
            nb += 1
        return nodes


class SplitStratifiedKFold(Splitter):
    """NodeStratifiedKFold Factory"""

    def __init__(self, y, n_folds):
        self.n_folds = n_folds
        self.y = y

    def produceNodes(self):
        nodes = []
        from sklearn.cross_validation import StratifiedKFold
        nb = 0
        ## Re-slice y
        for train, test in StratifiedKFold(y=self.y, n_folds=self.n_folds):
            nodes.append(NodeKFold(slices={NodeKFold.train_data_suffix: train,
                                          NodeKFold.test_data_suffix: test},
                                          nb=nb))
            nb += 1
        return nodes


class NodePermutation(NodeRowSlicer):
    """ Permutation parallelization node"""

    def __init__(self, n=None, n_perms=None, permutation=None, nb=None,
                 **kwargs):
        super(NodePermutation, self).__init__(slices=permutation,
            name="Permutation-" + str(nb), **kwargs)
        self.n = n
        self.n_perms = n_perms

class SplitPermutation(Splitter):
    """NodePermutation Factory"""

    def __init__(self, n, n_perms):
        self.n = n
        self.n_perms = n_perms

    def produceNodes(self):
        nodes = []
        from addtosklearn import Permutation
        nb = 0
        for perm in Permutation(n=self.n, n_perms=self.n_perms):
            nodes.append(NodePermutation(permutation=perm, nb=nb))
            nb += 1
        return nodes

# ------------ #
# -- Helper -- #
# ------------ #

def splitter_factory(cls, split_kwargs, job_kwargs):
    if cls.__name__ == "KFold":
        return SplitKFold(**split_kwargs)
    if cls.__name__ == "StratifiedKFold":
        return SplitStratifiedKFold(**split_kwargs)
    if cls.__name__ == "Permutation":
        return SplitPermutation(**split_kwargs)
    raise ValueError("Do not know how to build a splitter with %s" % (str(cls)))
        
PAR =  splitter_factory


# Data
X = np.asarray([[1, 2], [3, 4], [5, 6], [7, 8], [-1, -2], [-3, -4], [-5, -6], [-7, -8]])
y = np.asarray([1, 1, 1, 1, -1, -1, -1, -1])

from sklearn import svm
from sklearn import lda
from sklearn.cross_validation import KFold

if False:
    steps = (
    PAR(KFold, dict(n=X.shape[0], n_folds=4), dict()),
        N(svm.SVC, dict(kernel='linear')))

if False:
    from sklearn.feature_selection import SelectKBest
    steps = (
    PAR(KFold, dict(n=X.shape[0], n_folds=4), dict(n_jobs=5)),
        N(SelectKBest, dict(k=2)),
        N(svm.SVC, dict(kernel="linear")))

if True:
    from sklearn.feature_selection import SelectKBest
    from addtosklearn import Permutation
    steps = (
    PAR(Permutation, dict(n=X.shape[0], n_perms=2), dict(n_jobs=5)),
    PAR(KFold, dict(n=X.shape[0], n_folds=2), dict(n_jobs=5)),
        N(SelectKBest, dict(k=2)),
        N(svm.SVC, dict(kernel="linear")))

tree = Node(steps=steps, store="/tmp/store")
#[leaf.topdown(X=X, y=y) for leaf in tree]
#tree.reduce()

"""
epac : Embarrassingly Parallel Array Computing
"""
print __doc__


import numpy as np


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
            filename = Epac.config.store_fs_map_output_prefix + key2 +\
                Epac.config.store_fs_pickle_suffix
            file_path = os.path.join(path, filename)
            self.save_pickle(val2, file_path)

    def save_node(self, node):
        path = self.key2path(node.get_key())
        import os
        class_name = str(node.__class__).split(".")[-1].\
            replace(r"'", "").replace(r">", "")
        # try to save in json format
        filename = Epac.config.store_fs_node_prefix + class_name +\
            Epac.config.store_fs_json_suffix
        file_path = os.path.join(path, filename)
        if self.save_json(node.todict(), file_path):
            # saving in json failed => pickle
            filename = Epac.config.store_fs_node_prefix + class_name +\
            Epac.config.store_fs_pickle_suffix
            file_path = os.path.join(path, filename)
            self.save_pickle(node, file_path)

    def load_node(self, key):
        """Load a node given a key, recursive=True recursively walk through
        children"""
        path = self.key2path(key)
        import os
        prefix = os.path.join(path, Epac.config.store_fs_node_prefix)
        import glob
        file_path = glob.glob(prefix + '*')
        if len(file_path) != 1:
            raise IOError('Found no or more that one file in %s' % (prefix))
        file_path = file_path[0]
        _, ext = os.path.splitext(file_path)
        if ext == Epac.config.store_fs_json_suffix:
            node_dict = self.load_json(file_path)
            class_str = file_path.replace(prefix, "").\
                replace(Epac.config.store_fs_json_suffix, "")
            node = object.__new__(eval(class_str))
            node.__dict__.update(node_dict)
        elif ext == Epac.config.store_fs_pickle_suffix:
            node = self.load_pickle(file_path)
        else:
            raise IOError('File %s has an unkown extension: %s' %
                (file_path, ext))
        return node

    def load_map_output(self, key):
        path = self.key2path(key)
        import os
        import glob
        map_paths = glob.glob(os.path.join(path,
            Epac.config.store_fs_map_output_prefix) + '*')
        map_outputs = dict()
        for map_path in map_paths:
            ext = os.path.splitext(map_path)[-1]
            if ext == Epac.config.store_fs_pickle_suffix:
                map_obj = self.load_pickle(map_path)
            if ext == Epac.config.store_fs_json_suffix:
                map_obj = self.load_json(map_path)
            key = os.path.splitext(os.path.basename(map_path))[0].\
                replace(Epac.config.store_fs_map_output_prefix, "", 1)
            map_outputs[key] = map_obj
        return map_outputs

    def save_pickle(self, obj, file_path):
            import pickle
            output = open(file_path, 'wb')
            pickle.dump(obj, output)
            output.close()

    def load_pickle(self, file_path):
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
                json.dump(obj, output)
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
    if prot == Epac.config.key_prot_fs:
        return StoreFs()
    elif prot == Epac.config.key_prot_lo:
        return StoreLo(storage_root=Epac.roots[path])
    else:
        raise ValueError("Invalid value for key: should be:" +\
        "lo for no persistence and storage on living objects or" +\
        "fs and a directory path for file system based storage")


def key_split(key):
    return key.split(Epac.config.key_prot_path_sep, 1)


def key_join(prot="", path=""):
    return prot + Epac.config.key_prot_path_sep + path


def save_map_output(key1, key2=None, val2=None, keyvals2=None):
    store = get_store(key1)
    store.save_map_output(key1, key2, val2, keyvals2)


class Epac(object):
    """Parallelization node, provide:
        - key/val
        - I/O interface with the store."""

    # Static fields: config
    class config:
        store_fs_pickle_suffix = ".pkl"
        store_fs_json_suffix = ".json"
        store_fs_map_output_prefix = "__map__"
        store_fs_node_prefix = "__node__"
        key_prot_lo = "mem"  # key storage protocol: living object
        key_prot_fs = "file"  # key storage protocol: file system
        key_path_sep = "/"
        key_prot_path_sep = "://"  # key storage protocol / path separator

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
                self.name = key_join(prot=Epac.config.key_prot_lo,
                    path="".join(random.choice(string.ascii_uppercase +
                        string.digits) for x in range(10)))
                self.build_tree(steps, **kwargs)
            # store is a string and a valid directory , assume that storage
            # will be done on the file system, ie.: key prefix "fs://"
            elif isinstance(store, str):
                self.name = key_join(prot=Epac.config.key_prot_fs,
                                     path=store)
                self.build_tree(steps, **kwargs)
                self.save_node()
            else:
                raise ValueError("Invalid value for store: should be: " +\
                "None for no persistence and storage on living objects or " +\
                "a string path for file system based storage")
        # If not steps but store or key : load from fs store
        if not steps and (isinstance(store, str) or isinstance(key, str)):
            self.load_node(key=key, store=store)

    # Tree operations
    # ---------------
    def add_child(self, child):
        self.children.append(child)
        child.parent = self

    def add_children(self, children):
        for child in children:
            self.add_child(child)

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

    def transform(self, compose_from_root=True, **kwargs):
        if compose_from_root and self.parent:  # compose tranfo up to root
            kwargs = self.parent.transform(compose_from_root=True, **kwargs)
        return kwargs

    def get_name(self):
        return self.name

    def get_key(self):
        if not self.parent:
            return self.get_name()
        return Epac.config.key_path_sep.join(
            [self.parent.get_key(), self.get_name()])

    def get_leaves(self):
        if not len(self.children):
            return [self]
        else:
            leaves = []
            for child in self.children:
                leaves = leaves + child.get_leaves()
            return leaves

    def todict(self):
        ret = self.__dict__.copy()
        
        ret["children"] = [child.name for child in ret["children"] 
                                          if hasattr(child, "name")]
        if self.parent:
            ret["parent"] = self.parent.name
        return ret

    # Tree construction
    def build_tree(self, steps, **kwargs):
        """
        """
        if len(steps) == 0:
            return
        # If current step is a Parallelization node: a foactory of ParNode
        if isinstance(steps[0], ParNodeFactory):
            for child in steps[0].produceParNodes():
                self.add_children(child)
                child.build_tree(steps[1:], **kwargs)
        else:
            child = EstimatorWrapperNode(steps[0])
            self.add_children(child)
            child.build_tree(steps[1:], **kwargs)

    # I/O (persistance) operation
    def save_node(self, recursive=True):
        store = get_store(self.get_key())
        # prevent recursive saving of children/parent in a single dump
        children_save = self.children
        self.children = [child.name for child in self.children]
        parent_save = self.parent
        self.parent = ".."
        store.save_node(self)
        self.parent = parent_save
        self.children = children_save
        if recursive and len(self.children):
            for child in self.children:
                child.save_node(recursive=True)

    # I/O (persistance) operation
    @classmethod
    def load_node(cls, key=None, store=None, recursive=True):
        if key is None:
            key = key_join(prot=Epac.config.key_prot_fs,
                           path=store)
        #self.add_children(self.build_execution_tree(steps, data))
        store = get_store(key)
        node = store.load_node(key)
        # If Children: Recursively walk through children
        if recursive and len(node.children):
            for i in xrange(len(node.children)):
                child = node.children[i]
                child_key = Epac.config.key_path_sep.join([key, child])
                node.add_children(node.load_node(key=child_key,
                    recursive=True))
        return node

    # Iterate over leaves
    def __iter__(self):
        for leaf in self.get_leaves():
            yield leaf

    # Aggregation operations
    # ----------------------
    def aggregate(self):
        # Terminaison (leaf) node
        if len(self.children) == 0:
            return self.map_outputs
        # 1) Build sub-aggregates over children
        sub_aggregates = [child.aggregate() for child in self.children]
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

class EstimatorWrapperNode(Epac):

    """Node that wrap estimators"""
    def __init__(self, estimator, **kargs):
        self.estimator = estimator
        super(EstimatorWrapperNode, self).__init__(
            name=estimator.__class__.__name__, **kargs)

    def __repr__(self):
        return '%s(estimator=%s)' % (self.__class__.__name__,
            self.estimator.__repr__())


class ParNodeFactory(object):
    """Abstract class for Factories of parallelization nodes that implement
    produceParNodes"""

    def produceParNodes(self):
        raise NotImplementedError("Cannot call abstract method")


class ParSlicer(Epac):
    """Parallelization is based on several reslicing of the same dataset:
    Slices can be split (shards) or a resampling of the original datasets.
    """
    def __init__(self, transform_only=None, **kwargs):
        super(ParSlicer, self).__init__(**kwargs)
        self.transform_only = transform_only


class ParRowSlicer(ParSlicer):
    """Parallelization is based on several row-wise reslicing of the same
    dataset"""

    def __init__(self, slices, **kwargs):
        super(ParRowSlicer, self).__init__(**kwargs)
        # convert a as list if required
        if slices:
            self.slices =\
                [s.tolist() for s in slices if isinstance(s, np.ndarray)]

    def transform(self, compose_from_root=True, **kwargs):
        """ Transform inputs kwargs of array, and produce dict of array"""
        # Recusively compose the tranformations up to root's tree
        if compose_from_root and self.parent:
            kwargs = self.parent.transform(compose_from_root=True, **kwargs)
        if self.transform_only:
            keys = self.transform_only
        else:
            keys = kwargs.keys()
        res = kwargs.copy()
        for k in keys:
            res[k] = kwargs[k][self.slices[0]]
        return res


class ParKFold(ParRowSlicer, ParNodeFactory):
    """ KFold parallelization node"""

    def __init__(self, n=None, n_folds=None, slices=None, nb=None, **kargs):
        super(ParKFold, self).__init__(slices=slices,
            name="KFold-" + str(nb), **kargs)
        self.n = n
        self.n_folds = n_folds

    def produceParNodes(self):
        nodes = []
        from sklearn.cross_validation import KFold  # StratifiedKFold
        nb = 0
        for train_test in KFold(n=self.n, n_folds=self.n_folds):
            nodes.append(ParKFold(slices=train_test, nb=nb))
            nb += 1
        return nodes


class ParStratifiedKFold(ParRowSlicer):
    def __init__(self, slices, nb, **kargs):
        super(ParStratifiedKFold, self).__init__(slices=slices,
            name="KFold-" + str(nb), **kargs)


class ParPermutation(ParRowSlicer, ParNodeFactory):
    """ Permutation parallelization node

    2. implement the nodes ie.: the methods
       - fit and transform that modify the data during the "map" phase: the
         top-down (root to leaves) data flow
       - reduce that locally agregates the map results during the "reduce"
         phase: the bottom-up (leaves to root) data-flow.
    """
    def __init__(self, n=None, n_perms=None, permutation=None, nb=None,
                 **kargs):
        super(ParPermutation, self).__init__(slices=[permutation],
            name="Permutation-" + str(nb), **kargs)
        self.n = n
        self.n_perms = n_perms

    def produceParNodes(self):
        nodes = []
        from addtosklearn import Permutation
        nb = 0
        for perm in Permutation(n=self.n, n_perms=self.n_perms):
            nodes.append(ParPermutation(permutation=perm, nb=nb))
            nb += 1
        return nodes

# map and reduce functions
def mapfunc(key1, val1):
    X_test = val1["X"][1]
    y_test = val1["y"][1]
    keyvals2 = dict(
        mean=dict(pred=np.sign(np.mean(X_test, axis=1)), true=y_test),
        med=dict(pred=np.sign(np.median(X_test, axis=1)), true=y_test))
    save_map_output(key1, keyvals2=keyvals2)


def reducefunc(key2, val2):
    mean_pred = np.asarray(val2['pred'])
    mean_true = np.asarray(val2['true'])
    accuracies = np.sum(mean_true == mean_pred, axis=-1)
    accuracies_cv_mean = np.mean(accuracies, axis=-1)
    accuracies_perm_pval = np.sum(accuracies_cv_mean[1:] >
        accuracies_cv_mean[0])
    return dict(method=key2, accuracies_cv_mean=accuracies_cv_mean,
                accuracies_perm_pval=accuracies_perm_pval)

# Data
X = np.asarray([[1, 2], [3, 4], [5, 6], [7, 8], [-1, -2], [-3, -4], [-5, -6], [-7, -8]])
y = np.asarray([1, 1, 1, 1, -1, -1, -1, -1])

kwargs = dict(X=X, y=y)

from sklearn import svm
steps = (ParKFold(n=X.shape[0], n_folds=2),
         svm.SVC(kernel='linear'))

root = Epac(steps=steps, store="/tmp/store", X=X, y=y)
#root2 = Epac(store="/tmp/store")

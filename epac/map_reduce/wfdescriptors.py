# -*- coding: utf-8 -*-
"""
Created on Fri Oct 18 10:42:47 2013

@author: jinpeng.li@cea.fr
"""

import os
from epac import StoreFs
from epac.map_reduce.exports import save_job_list
from epac.map_reduce.split_input import SplitNodesInput
from epac.map_reduce.inputs import NodesInput


def export_bash_jobs(filename, map_cmds, reduce_cmds):
    fileout = open(filename, "w+")
    for map_cmd in map_cmds:
        cmd_str = ""
        for cmd in map_cmd:
            cmd_str = cmd_str + cmd + " "
        fileout.write(cmd_str + "\n")
    for reduce_cmd in reduce_cmds:
        cmd_str = ""
        for cmd in reduce_cmd:
            cmd_str = cmd_str + cmd + " "
        fileout.write(cmd_str + "\n")
    fileout.close()


class WorkflowDescriptor(object):
    '''
    Parameters
    ----------
    dataset_dir_path: string
        The path which the saved dataset located. You can use
        epac.utils.save_dataset_path or epac.utils.save_dataset_path
        to save dictionary. Some examples are shown in
        epac.utils.save_dataset_path and epac.utils.save_dataset.
    epac_tree_dir_path: string
        The path where the epac tree is located.
    out_dir_path: string
        The path where the results have been saved.

    Example
    -------
    # =================================================================
    # Build dataset dir
    # =================================================================
    from sklearn import datasets
    from epac.utils import save_dataset_path
    import numpy as np
    X, y = datasets.make_classification(n_samples=500,
                                        n_features=500,
                                        n_informative=2,
                                        random_state=1)
    path_X = "/tmp/data_X.npy"
    path_y = "/tmp/data_y.npy"
    np.save(path_X, X)
    np.save(path_y, y)
    dataset_dir_path = "/tmp/dataset"
    path_Xy = {"X":path_X, "y":path_y}
    save_dataset_path(dataset_dir_path, **path_Xy)

    # =================================================================
    # Build epac tree (epac workflow) and save them on disk
    # =================================================================
    import os
    from epac import Methods
    from epac import StoreFs
    from sklearn.svm import LinearSVC as SVM
    epac_tree_dir_path = "/tmp/tree"
    if not os.path.exists(epac_tree_dir_path):
        os.makedirs(epac_tree_dir_path)
    multi = Methods(SVM(C=1), SVM(C=10))
    store = StoreFs(epac_tree_dir_path, clear=True)
    multi.save_tree(store=store)

    # =================================================================
    # Export scripts to workflow directory
    # =================================================================
    from epac.map_reduce.wfdescriptors import WorkflowDescriptor
    # to save results in outdir, for example, the results of reducer
    out_dir_path = "/tmp/outdir"
    workflow_dir = "/tmp/workflow"
    wf_desc = WorkflowDescriptor(dataset_dir_path,
                                 epac_tree_dir_path,
                                 out_dir_path)
    wf_desc.export(workflow_dir=workflow_dir, num_processes=2)

    '''
    def __init__(self, dataset_dir_path, epac_tree_dir_path, out_dir_path):
        self.dataset_dir_path = dataset_dir_path
        self.epac_tree_dir_path = epac_tree_dir_path
        self.out_dir_path = out_dir_path

    def export(self, workflow_dir, num_processes):
        '''
        Parameters
        ----------
        workflow_dir: string
            the directory to export workflow
        num_processes: integer
            the number of processes you want to run
        '''
        self.workflow_dir = workflow_dir
        if not os.path.exists(self.workflow_dir):
            os.makedirs(self.workflow_dir)
        store_fs = StoreFs(dirpath=self.epac_tree_dir_path)
        tree_root = store_fs.load()
        node_input = NodesInput(tree_root.get_key())
        split_node_input = SplitNodesInput(tree_root,
                                           num_processes=num_processes)
        nodesinput_list = split_node_input.split(node_input)
        keysfile_list = save_job_list(workflow_dir, nodesinput_list)
        map_cmds = []
        reduce_cmds = []
        for i in xrange(len(keysfile_list)):
            key_path = os.path.join(workflow_dir, keysfile_list[i])
            map_cmd = []
            map_cmd.append("epac_mapper")
            map_cmd.append("--datasets")
            map_cmd.append(self.dataset_dir_path)
            map_cmd.append("--keysfile")
            map_cmd.append(key_path)
            map_cmd.append("--treedir")
            map_cmd.append(self.epac_tree_dir_path)
            map_cmds.append(map_cmd)
        reduce_cmd = []
        reduce_cmd.append("epac_reducer")
        reduce_cmd.append("--treedir")
        reduce_cmd.append(self.epac_tree_dir_path)
        reduce_cmd.append("--outdir")
        reduce_cmd.append(self.out_dir_path)
        reduce_cmds.append(reduce_cmd)
        filename_bash_jobs = os.path.join(workflow_dir, "bash_jobs.sh")
        export_bash_jobs(filename_bash_jobs, map_cmds, reduce_cmds)


class SomaWorkflowDescriptor(WorkflowDescriptor):
    '''
    Example
    -------
    # =================================================================
    # Build dataset dir
    # =================================================================
    from sklearn import datasets
    from epac.utils import save_dataset_path
    import numpy as np
    X, y = datasets.make_classification(n_samples=500,
                                        n_features=500,
                                        n_informative=2,
                                        random_state=1)
    path_X = "/tmp/data_X.npy"
    path_y = "/tmp/data_y.npy"
    np.save(path_X, X)
    np.save(path_y, y)
    dataset_dir_path = "/tmp/dataset"
    path_Xy = {"X":path_X, "y":path_y}
    save_dataset_path(dataset_dir_path, **path_Xy)

    # =================================================================
    # Build epac tree (epac workflow) and save them on disk
    # =================================================================
    import os
    from epac import Methods
    from epac import StoreFs
    from sklearn.svm import LinearSVC as SVM
    epac_tree_dir_path = "/tmp/tree"
    if not os.path.exists(epac_tree_dir_path):
        os.makedirs(epac_tree_dir_path)
    multi = Methods(SVM(C=1), SVM(C=10))
    store = StoreFs(epac_tree_dir_path, clear=True)
    multi.save_tree(store=store)

    # =================================================================
    # Export scripts to workflow directory
    # =================================================================
    from epac.map_reduce.wfdescriptors import SomaWorkflowDescriptor
    # to save results in outdir, for example, the results of reducer
    out_dir_path = "/tmp/outdir"
    workflow_dir = "/tmp/workflow"
    swf_desc = SomaWorkflowDescriptor(dataset_dir_path,
                                     epac_tree_dir_path,
                                     out_dir_path)
    swf_desc.export(workflow_dir=workflow_dir, num_processes=2)
    '''
    def __init__(self, dataset_dir_path, epac_tree_dir_path, out_dir_path):
        super(SomaWorkflowDescriptor, self).__init__(dataset_dir_path,
                                                     epac_tree_dir_path,
                                                     out_dir_path)

    def export(self, workflow_dir, num_processes):
        from soma_workflow.client import Job
        from soma_workflow.client import Group
        from soma_workflow.client import Workflow
        from soma_workflow.client import SharedResourcePath
        from soma_workflow.client import FileTransfer
        from soma_workflow.client import Helper
        # dataset on remote machine
        dataset_dir = SharedResourcePath(relative_path="dataset",
                                         namespace="EPAC",
                                         uuid="soma_workflow_shared_dir")
        # Tree on remote machine
        epac_tree_dir = SharedResourcePath(relative_path="tree",
                                           namespace="EPAC",
                                           uuid="soma_workflow_shared_dir")
        # Reduce output on remote machine
        out_dir =  FileTransfer(is_input=False,
                                       client_path="/tmp/out_dir",
                                       name="reduce_output")
        # workflow file for soma-workflow
        soma_workflow_file = os.path.join(workflow_dir,
                                          "soma_workflow")
        # Split tree for each map task
        self.workflow_dir = workflow_dir
        if not os.path.exists(self.workflow_dir):
            os.makedirs(self.workflow_dir)
        store_fs = StoreFs(dirpath=self.epac_tree_dir_path)
        tree_root = store_fs.load()
        node_input = NodesInput(tree_root.get_key())
        split_node_input = SplitNodesInput(tree_root,
                                           num_processes=num_processes)
        nodesinput_list = split_node_input.split(node_input)
        keysfile_list = save_job_list(workflow_dir, nodesinput_list)
        # Building mapper task
        dependencies = []
        map_jobs = []
        for i in xrange(len(keysfile_list)):
            key_path = os.path.join(workflow_dir, keysfile_list[i])
            map_cmd = []
            map_cmd.append("epac_mapper")
            map_cmd.append("--datasets")
            map_cmd.append(dataset_dir)
            map_cmd.append("--keysfile")
            map_cmd.append(key_path)
            map_cmd.append("--treedir")
            map_cmd.append(epac_tree_dir)
            map_job = Job(command=map_cmd,
                          name="map_step",
                          referenced_input_files=[],
                          referenced_output_files=[])
            map_jobs.append(map_job)
        group_map_jobs = Group(elements=map_jobs, name="all map jobs")
        # Building reduce step
        reduce_cmd = []
        reduce_cmd.append("epac_reducer")
        reduce_cmd.append("--treedir")
        reduce_cmd.append(epac_tree_dir)
        reduce_cmd.append("--outdir")
        reduce_cmd.append(out_dir)
        reduce_job = Job(command=reduce_cmd,
                         name="reduce_step",
                         referenced_input_files=[],
                         referenced_output_files=[out_dir])
        for map_job in map_jobs:
            dependencies.append((map_job, reduce_job))
        jobs = map_jobs + [reduce_job]
        # Build workflow and save into disk
        workflow = Workflow(jobs=jobs,
                            dependencies=dependencies,
                            root_group=[group_map_jobs,
                                        reduce_job])
        Helper.serialize(soma_workflow_file, workflow)

if __name__ == "__main__":
    import doctest
    doctest.testmod()

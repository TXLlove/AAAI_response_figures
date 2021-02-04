import argparse

# import torch
import numpy as np
import time as tt

# import models
from models.functions import dp_solver, ippp, heuristic, ippp_start, val

parser = argparse.ArgumentParser(description='IPPP validation on S-ResNet-18-CIFAR10')
parser.add_argument('--gain', default=0.45, type=float, 
                    help='constraint on latency gain')
parser.add_argument('--exp', dest='experiment', action='store_true',
                    help='perform the paper experiment')
parser.add_argument('--eta', default=100, type=float, 
                    help='smoothness parameter of iPPP')
parser.add_argument('--mu', default=1, type=float, 
                    help='convexity parameter of iPPP')
parser.add_argument('--beta', default=5e2, type=float, 
                    help='penalty parameter of iPPP, default: 3e2')
parser.add_argument('--gamma', default=10, type=float, 
                    help='proximal parameter of iPPP')
parser.add_argument('--k', default=30, type=float, 
                    help='shape parameter of iPPP')
parser.add_argument('--T', default=100, type=float, 
                    help='outer interative number of iPPP')
parser.add_argument('--J', default=10, type=float, 
                    help='inner interative number of iPPP')

candidates = [-0.2 * i for i in range(6)]
num_gain = 100
low_latency = 0.375
up_latency = 0.635

baseline_time = 1.0
avg_b_time = [0.32, 0.53, 0.76, 1.0, 1.07]

class f_model:

    def __init__(self, baseline_time, avg_b_time):
        super(f_model, self).__init__()
        self.baseline_time = baseline_time
        self.avg_b_time = avg_b_time

def main():
    args = parser.parse_args()
    main_worker(args)

def main_worker(args):

    model = f_model(baseline_time, avg_b_time)

    train_cor = np.load('./experiment_data/Scan_val_correct.npy') 
    train_cfd = np.load('./experiment_data/Scan_val_confidence.npy')

    val_cor = np.load('./experiment_data/Scan_test_correct.npy') 
    val_cfd = np.load('./experiment_data/Scan_test_confidence.npy')

    f_list = [heuristic, ippp]
    # f_list = [heuristic, ippp_start, ippp, dp_solver, ippp]
    # f_list = [ippp_start, ippp, dp_solver, ippp]
    threshold = None

    if not args.experiment:

        for f in f_list:

            if f == ippp:
                start = tt.time()
                threshold = ippp_start(model, train_cor, train_cfd, args.gain * model.baseline_time, -1.0, args)
                threshold = f(model, train_cor, train_cfd, threshold, args.gain * model.baseline_time, -1.0, args)
                print('execution time: {t:.5f}'.format(t=tt.time() - start))
            elif f == ippp_start:
                threshold = f(model, train_cor, train_cfd, args.gain * model.baseline_time, -1.0, args)
            elif f == heuristic:
                threshold = f(train_cfd, model.avg_b_time, args.gain * model.baseline_time)
            else:
                threshold = f(model, train_cor, train_cfd, candidates, args.gain * model.baseline_time)

            acc, time = val(threshold, train_cor, train_cfd, model.avg_b_time)
            print('Train: {name} * Acc@1 {top1:.3f} Gain {t_gain:.5f}'.format(name=f.__name__, top1=acc, t_gain=time))
            acc, time = val(threshold, val_cor, val_cfd, model.avg_b_time)
            print('Val: {name} * Acc@1 {top1:.3f} Gain {t_gain:.5f}'.format(name=f.__name__, top1=acc, t_gain=time))

        return

    acc_train = np.zeros((num_gain, len(f_list)+1))
    delay_train = np.zeros((num_gain, len(f_list)+1))
    acc_val = np.zeros((num_gain, len(f_list)+1))
    delay_val = np.zeros((num_gain, len(f_list)+1))
    
    exec_time = np.zeros((num_gain, ))
    
    interval = (up_latency - low_latency)/num_gain

    for i, latency in enumerate([low_latency + interval * (i+1) for i in range(num_gain)]):
        print('=> Perform experiment {current}/{total}: {gain_i}'.format(current=i+1, total=num_gain, gain_i=latency/model.baseline_time))
        acc_train[i, 0], delay_train[i, 0], acc_val[i, 0], delay_val[i, 0] = latency, latency, latency, latency

        for j, f in enumerate(f_list):

            if f == ippp:
                start = tt.time()
                threshold = ippp_start(model, train_cor, train_cfd, latency, -1.0, args)
                threshold = f(model, train_cor, train_cfd, threshold, latency, -1.0, args)
                exec_time[i] = tt.time() - start
            elif f == ippp_start:
                threshold = f(model, train_cor, train_cfd, latency, -1.0, args)
            elif f == heuristic:
                threshold = f(train_cfd, model.avg_b_time, latency)
            else:
                threshold = f(model, train_cor, train_cfd, candidates, latency)

            acc_train[i, j+1], delay_train[i, j+1] = val(threshold, train_cor, train_cfd, model.avg_b_time)
            print('Train: {name} * Acc@1 {top1:.3f} Gain {t_gain:.5f}'.format(name=f.__name__, top1=acc_train[i, j+1], t_gain=delay_train[i, j+1]))
            acc_val[i, j+1], delay_val[i, j+1] = val(threshold, val_cor, val_cfd, model.avg_b_time)
            print('Val: {name} * Acc@1 {top1:.3f} Gain {t_gain:.5f}'.format(name=f.__name__, top1=acc_val[i, j+1], t_gain=delay_val[i, j+1]))
    
    print('execution time: avg {avg:.5f} std {std:.5f}'.format(avg=np.mean(exec_time), std=np.std(exec_time)))

    np.save('./experiment_result/Scan_ippp_train_acc', acc_train)
    np.save('./experiment_result/Scan_ippp_train_delay', delay_train)
    np.save('./experiment_result/Scan_ippp_val_acc', acc_val)
    np.save('./experiment_result/Scan_ippp_val_delay', delay_val)

if __name__ == '__main__':
    main()
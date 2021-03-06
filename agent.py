import numpy as np
import time
import random
from car_parking_env import car_sim_env
from car_parking_env import Agent
import os, sys, termios, tty
import re
from collections import namedtuple
import cPickle
import threading
import argparse
from PIL import Image
from shutil import copyfile
from datetime import datetime

from model.model import DQN
from tools import print_log
from tools import ReplayMemory

import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import torchvision.transforms as T
import torchvision



parser = argparse.ArgumentParser(description='Model parameters')
parser.add_argument('-d', '--discount', default=0.8, type=float, help='Discount value(gamma) for Discounted Return')
parser.add_argument('-e', '--epsilon', default=0.95, type=float, help='Exploration rate')
parser.add_argument('-ed', '--eps_decay', default=0.99, type=float, help='Epsilon decay rate')
parser.add_argument('-batch', '--BATCH_SIZE', default=32, type=int, help='Batch size')
parser.add_argument('-o', '--observe', default=5, type=int, help='Observation frequency')
parser.add_argument('-lr', '--lrate', default=0.01, type=float, help='Learning rate of DNN')
parser.add_argument('--TARGET_UPDATE_CYCLE', default=10, type=int, help='Target_net Update Cycle')
parser.add_argument('--path', default='./data/', type=str, help='saved state image data_path')
parser.add_argument('--SAVE_PATH', default='./log/', type=str, help='')
parser.add_argument('--MEMORY_SIZE', default=10000, type=int, help='ReplayMemory capacity')
parser.add_argument('--log', default=None, help='open log')
parser.add_argument('--TEST_INTERVAL', default=100, type=int, help='evaluation inverval')

args = parser.parse_args()

filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
log = open(os.path.join(args.SAVE_PATH, 'RLPark_Log_'+filename+'.txt'), 'w')
args.log = log

Transition = namedtuple('Transition', ('state', 'action', 'next_state', 'reward'))
state = namedtuple('state', ('state_img', 'state_tuple'))
state_tuple = namedtuple('state_tuple', ('x', 'y', 'theta_heading', 's', 'theta_steering'))


print_log("pytorch version : {}".format(torch.__version__), log)
print_log("------[Initial parameters]------", log)
print_log("Initial epsilon: {}".format(args.epsilon), log)
print_log("Epsilon decay rate: {}".format(args.eps_decay), log)
print_log("Batch size: {}".format(args.BATCH_SIZE), log)
print_log("Learning rate: {}".format(args.lrate), log)
print_log("Discount factor(gamma): {}".format(args.discount), log)

#print "==========>", linear1.device
#print "==========>", self.linear1.weight.device

class LearningAgent(Agent):
    """An agent that learns to automatic parking"""

    def __init__(self, env, is_test = False):
        super(LearningAgent, self).__init__()
        self.test = is_test
        self.env = env

        self.epsilon_start = args.epsilon
        self.epsilon_decay = args.eps_decay
        self.epsilon_end = 0.05

        if not self.test:
            self.epsilon = self.epsilon_start
        else:
            self.epsilon = 0.0

        self.learning_rate = args.lrate
        self.batch_size = args.BATCH_SIZE
        self.gamma = args.discount

        self.state = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
#        self.device = torch.device("cpu")
        if torch.cuda.is_available() :
            print "using cuda..."
        else :
            print "using cpu..."

        self.memory = ReplayMemory(args.MEMORY_SIZE)
        
        self.policy_net = DQN(vec_size=5, n_actions=9).to(self.device)
        self.target_net = DQN(vec_size=5, n_actions=9).to(self.device)
#        self.policy_net = DQN(vec_size=5, n_actions=9).cuda()
#        self.target_net = DQN(vec_size=5, n_actions=9).cuda()
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()
        
        self.optimizer = optim.RMSprop(self.policy_net.parameters(), lr= 1e-2)
        print "device", self.device
        print "q net", self.policy_net
        print "target net", self.target_net

        if 1 :
            self.state_path = 'state.png'
            
            init_path = os.path.join(args.path, '../env.png')    
            cp_path = os.path.join(args.path, self.state_path)
            copyfile(init_path, cp_path)
            self.env.update_screen()

#    def load_dataset(self, path):i
#        train_dataset = torchvision.datasets.ImageFolder(
#            root = path,
#            transform = T.toTensor()
#        )
#        data_loader = torch.utils.data.DataLoader(
#            train_dataset,
#            batch_size = self.batch_size,
#            num_workers = 0,
#            shuffle = False
#        )
#        return data_loader

    # Retrieve screens saved by car_parking_env.py/captureStates and convert them to tensor
    '''
    def get_screen(self):
        downsample_size = 80, 60
        if os.path.isdir(args.path):
#            if is_capture_env :
#                state_path = os.path.join(args.path, '../env.png')                
#                cp_path = os.path.join(args.path, self.state_path)
#                copyfile(state_path, cp_path)
            state_path = os.path.join(args.path, self.state_path)

            if os.path.isfile(state_path):
                try:
                    state_img = Image.open(state_path).convert('L') # Open as grayscale
                    state_img.thumbnail(downsample_size, Image.ANTIALIAS)
                    #print('State: ', state_img)
                    state = np.array(state_img)
                    state = torch.from_numpy(state)
#                    state1 = state
#                    state = state.unsqueeze(0) # Add channel dimension - (C, H, W)
#                    print "\timage =>", state
                    state = state.type('torch.FloatTensor')
#                    state = torchvision.transforms.Normalize(0.0, 1.0)(state)
                    state = state/255.
#                    torchvision.utils.save_image(state, './data/_tmp.jpg')
                    state = state.view(1,60,80).to(self.device)
#                    for _ in range(60) :
#                        print "\timage", state[0][_]
#                    print "\timage_shape =>", state.size()
                except IOError:
                    print ("Could not open '%s'" % state_path)
            else:
                print_log("Error : there is no state_path => {}".format(state_path), log)
        else :
            print_log("Error : there is no args.path => {}".format(args.path), log)

        self.env.state_img = state

        return state
    '''
    def update_epsilon(self):
        if self.epsilon >= self.epsilon_end:
            self.epsilon *= self.epsilon_decay
        #print "Exploration rate: ", self.epsilon

    def optimize_model(self, memory):
        if len(memory.memory) < args.BATCH_SIZE :
            return
        transitions = memory.sample(args.BATCH_SIZE)
#        print "transition ", transitions.size()
        batch = Transition(*zip(*transitions))
#        print "\ttransition \t", batch

        non_final_mask = torch.tensor(
                tuple(map(lambda s: s is not None, batch.next_state)), 
                dtype=torch.uint8).to(self.device)
        non_final_next_s_img = torch.cat([s[0] for s in batch.next_state if s is not None])
        non_final_next_s_tuple = torch.cat([s[1] for s in batch.next_state if s is not None]).view(-1, 5)

        s_img_batch = torch.cat([s[0] for s in batch.state])
#        print "\t\t state_img ", s_img_batch
        s_tuple_batch = torch.cat([s[1] for s in batch.state]).view(-1, 5)
#        print "\t\t state_tuple", s_tuple_batch
        a_batch = torch.cat(batch.action).view(args.BATCH_SIZE, -1)
        r_batch = torch.cat(batch.reward)

#        print "a_batch.size : ", a_batch.size()
#        print "\ta_batch : ", a_batch

        Q = self.policy_net(s_img_batch, s_tuple_batch)
#        print "QQQQQ ", Q.data.size()
#        print "\tQ : ", Q
        Q = Q.gather(1, a_batch)
#        print "\tQ_gather : ", Q

#        s_img = state[0]
#        s_v = torch.Tensor([state[1] for i in range(BATCH_SIZE)], device=self.device).view(BATCH_SIZE, -1)
#        next_s_img = next_state[0]
#        next_s_v = torch.Tensor([next_state[1] for i in range(BATCH_SIZE)], device=self.device).view(BATCH_SIZE, -1)

#        print "action : ", action
#        print "action_int : ", car_sim_env.valid_actions.index(action)
#        action = torch.LongTensor([car_sim_env.valid_actions.index(action)])
#        print "action ====", action
#        print "action_tensor : ", action
#        Q = self.policy_net(state).gather(1, action)
#        print "QQ", Q.data.size()
#        print "Q", Q
#        Q = Q.index_select(dim=0, index=action)
#        print "Q_ind", Q
        V_next = torch.zeros(args.BATCH_SIZE, device=self.device)
        V_next[non_final_mask] = self.target_net(
                non_final_next_s_img, non_final_next_s_tuple
                ).max(1)[0].detach()

#        print_log("\treward : {}".format(r_batch), log)
        expected_Q = (V_next * self.gamma) + r_batch

        loss = F.smooth_l1_loss(Q, expected_Q.unsqueeze(1))

        self.optimizer.zero_grad()
        loss.backward()
        for param in self.policy_net.parameters():
            param.grad.data.clamp_(-1, 1)
        self.optimizer.step()


    def update(self):
        if self.state == None: # init
            agent_pose = self.env.sense()
            self.state = state(
                    state_img = self.env.get_screen().to(self.device),
                    state_tuple = torch.Tensor(state_tuple(
                        x = agent_pose[0],
                        y = agent_pose[1],
                        theta_heading = agent_pose[2],
                        s = agent_pose[3],
                        theta_steering = agent_pose[4]
                        )).to(self.device)
                    )

        step = self.env.get_steps()
        if self.env.enforce_deadline:
            deadline = self.env.get_deadline()

        self.env._image_show()
        # Select action according to your policy
        action = self.get_action(self.state)
        # Execute action and get reward
        next_agent_pose,reward = self.env.act(self, action)
        # s_img update : screen plt update
        self.env.update_screen()
        
        self.next_state = state(
                state_img = self.env.get_screen().to(self.device),
                state_tuple = torch.Tensor(state_tuple(
                    x=next_agent_pose[0], 
                    y=next_agent_pose[1], 
                    theta_heading=next_agent_pose[2], 
                    s=next_agent_pose[3], 
                    theta_steering=next_agent_pose[4]
                    )).to(self.device)
                )

        # Learn policy based on state, action, reward
        if not self.test:
            self.memory.push(
                    self.state, 
                    torch.LongTensor([car_sim_env.valid_actions.index(action)]).to(self.device), 
                    self.next_state,
                    torch.Tensor([reward]).to(self.device)
                    )
            self.optimize_model(self.memory)

        self.state = self.next_state
    
    def get_action(self, state): 
        s_img = state[0].view(1,1,60,80)
        s_tuple = state[1].view(1,5)
        
        if random.random() > self.epsilon :
            with torch.no_grad():
                q_values = self.policy_net(s_img, s_tuple)
                print "\tq_values", q_values
                action_selected = car_sim_env.valid_actions[q_values.argmax(dim=1, keepdim=False)]
#                print "\tget_action : act", (action_selected)
        else :
            action_selected = random.choice(car_sim_env.valid_actions)

        return action_selected


def run(restore):
    env = car_sim_env()
    agt = LearningAgent(env, is_test=False)
    env.set_agent(agt, enforce_deadline=False)


    #train_thread = threading.Thread(name="train", target=train, args=(env, agt, restore))
    #train_thread.daemon = True # exit sub_threading when main_threading is done
    #train_thread.start()
   
    #plt_thread = threading.Thread(name="env.plt_show()", target=env.plt_show(), args=())
    #plt_thread.daemon = True
    #plt_thread.start()

    env.plt_show()
    train(env, agt, restore)
    while True:
        continue

def _replayMemoryImageCheck_forTest(agt, dir_idx) :
    m = agt.memory
    DATA_DIR_CUR = './data/{}_replaymemory_cur'.format(dir_idx)
    DATA_DIR_NEXT = './data/{}_replaymemory_next'.format(dir_idx)

    try:
        if not os.path.isdir(DATA_DIR_CUR) :
            print "Data directory does not exist: Invalid."
            print "Creating ./data directory..."
            os.mkdir(DATA_DIR_CUR)
        
        if not os.path.isdir(DATA_DIR_NEXT) :
            #torchvision.transforms.ToPILImage()(x)
            print "Data directory does not exist: Invalid."
            print "Creating ./data directory..."
            os.mkdir(DATA_DIR_NEXT)

        if 1 :
#            x = []
            for i in range(len(m.memory)):
                x_c = m.memory[i].state.state_img
                #x_t = m.memory[i][0][0]
                save_path_cur = os.path.join(DATA_DIR_CUR, 'state{}.png'.format(i))
                torchvision.utils.save_image(x_c, save_path_cur)
                
                x_n = m.memory[i].next_state.state_img
                save_path_next = os.path.join(DATA_DIR_NEXT, 'state{}.png'.format(i))
                torchvision.utils.save_image(x_n, save_path_next)
                #x_t = T.functional.to_pil_image(x_t)
                #x.append(x_t)
            
#            state = os.path.join(DATA_DIR, 'state{}.png'.format(idx))
#            idx = 0
#            while not os.path.isfile(state) :
#                self.env_fig.savefig(state)
#                idx += 1
#                state = os.path.join(DATA_DIR, 'state{}.png'.format(idx))

    except OSError:
        print "mkdir failed: Creating a new dir failed."

def train(env, agt, restore):
    n_trials = 9999999999
    quit = False
    max_index = 0
    for trial in xrange(max_index + 1, n_trials):
        # time.sleep(3)
        print "\tSimulator.run(): Trial {}".format(trial)  # [debug]
        if not agt.test:
            if trial > 80000 and trial < 150000:
                agt.epsilon = 0.3
            elif trial > 150000 and trial < 250000:
                agt.epsilon = 0.2
            elif trial > 250000:
                agt.epsilon =20000 / float(trial)  # changed to this when trial >= 2300000

        env.reset()

        while True:
            try:
                agt.update()
                env.step()
            except KeyboardInterrupt:
                quit = True
            finally:
                if env.done or quit:
                    agt.update_epsilon()
                    break
        if trial % args.TARGET_UPDATE_CYCLE == 0 :
            agt.target_net.load_state_dict(agt.policy_net.state_dict())

        if trial % args.TEST_INTERVAL == 0:
            _replayMemoryImageCheck_forTest(agt, trial)

            total_runs = env.succ_times + env.hit_wall_times + env.hit_car_times + env.num_hit_time_limit \
                         + env.num_out_of_time
            succ_rate = env.succ_times / float(total_runs)
            hit_cars_rate = env.hit_car_times / float(total_runs)
            hit_wall_rate = env.hit_wall_times / float(total_runs)
            hit_hard_time_limit_rate = env.num_hit_time_limit  / float(total_runs)
            out_of_time_rate = env.num_out_of_time / float(total_runs)
            
            print_log('***********************************************************************', log)
            print_log('n_episode:{}'.format(trial), log)
            print_log('successful trials / total runs: {}/{}'.format(env.succ_times, total_runs), log)
            print_log('number of trials that hit cars: {}'.format(env.hit_car_times), log)
            print_log('number of trials that hit walls: {}'.format(env.hit_wall_times), log)
            print_log('number of trials that hit the hard time limit: {}'.format(env.num_hit_time_limit), log)
            print_log('number of trials that ran out of time: {}'.format(env.num_out_of_time), log)
            print_log('successful rate: {}'.format(succ_rate), log)
            print_log('hit cars rate: {}'.format(hit_cars_rate), log)
            print_log('hit wall rate: {}'.format(hit_wall_rate), log)
            print_log('hit hard time limit rate: {}'.format(hit_hard_time_limit_rate), log)
            print_log('out of time rate: {}'.format(out_of_time_rate), log)
            print_log('**********************************************************************', log)
            '''
            if agt.test:
                rates_file = os.path.join(data_path, 'rates' + '.cpickle')
                rates={}
                if os.path.exists(rates_file):
                    with open(rates_file, 'rb') as f:
                        rates = cPickle.load(f)
                        os.remove(rates_file)
                rates[trial] = {'succ_rate':succ_rate, 'hit_cars_rate':hit_cars_rate, 'hit_wall_rate':hit_wall_rate, \
                                 'hit_hard_time_limit_rate':hit_hard_time_limit_rate, 'out_of_time_rate':out_of_time_rate}

                with open(rates_file, 'wb') as f:
                    cPickle.dump(rates, f, protocol=cPickle.HIGHEST_PROTOCOL)
            '''
            
            env.clear_count()

        '''
        if not agt.test:
            if trial % 2000 == 0:
                print "Trial {} done, saving Q table...".format(trial)
                q_table_file = os.path.join(data_path, 'trial' + str('{:010d}'.format(trial)) + '.cpickle')
                with open(q_table_file, 'wb') as f:
                    cPickle.dump(agt.Q_values, f, protocol=cPickle.HIGHEST_PROTOCOL)

            if quit:
                break
        '''

if __name__ == '__main__':
    run(restore = True)




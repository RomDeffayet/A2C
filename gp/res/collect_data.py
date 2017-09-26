import numpy as np
import tensorflow as tf
from tqdm import tqdm

from gp.a2c.a2c import A2C
from gp.a2c.envs.gym_env import GymEnv
from gp.utils.utils import create_dirs

FLAGS = tf.app.flags.FLAGS
tf.app.flags.DEFINE_string('save_dir', "./data/", """ directory to save to """)
tf.app.flags.DEFINE_integer('episodes', 500, """ number of episodes """)
tf.app.flags.DEFINE_integer('episode_len', 45, """ number of episode steps """)
tf.app.flags.DEFINE_integer('max_episode_len', 5001, """ number of episode steps """)
import matplotlib.pyplot as plt


class Collector:
    def __init__(self, env_id, make_enviroments, policy):
        create_dirs([FLAGS.save_dir])
        self.env = make_enviroments(num_envs=1, env_class=GymEnv, env_name=env_id, seed=42)
        self.action_dims = self.env.action_space.n
        self.state_size = self.env.observation_space.shape

        self.states = np.zeros((FLAGS.episodes, FLAGS.episode_len + 1) + self.state_size)
        self.rewards = np.zeros((FLAGS.episodes, FLAGS.episode_len))
        self.actions = np.zeros((FLAGS.episodes, FLAGS.episode_len))
        self.action_space = np.arange(self.action_dims)
        self.epsd_cnt = np.zeros((1,))
        self.policy = policy

    def observation_update(self, new_observation, old_observation):
        updated_observation = np.roll(old_observation, shift=-1, axis=3)
        updated_observation[:, :, :, -1] = new_observation[:, :, :, 0]
        return updated_observation

    def collect_data(self):
        ob = self.env.reset()
        ob = np.concatenate((ob, ob, ob, ob), axis=-1)
        epsd = 0
        while epsd < FLAGS.episodes:
            states = np.zeros((FLAGS.max_episode_len + 1,) + self.state_size)
            rewards = np.zeros((FLAGS.max_episode_len))
            actions = np.zeros((FLAGS.max_episode_len))
            print('episode: ', epsd)
            for step in tqdm(range(FLAGS.max_episode_len)):
                policy_action, _ = self.policy(ob)
                action = self.action_space[policy_action]

                # print(action)
                self.env.render()

                new_ob, reward, done, _ = self.env.step([action])
                states[step] = new_ob[0]
                rewards[step] = reward
                actions[step] = action

                # for debugging purposes
                # if step%10 in range(10) :
                #     plt.imsave('./data_samples/'+str(step)+'jpg',new_ob[0,:,:,0],cmap='gray')
                # print(reward)
                ob = self.observation_update(new_ob, ob)
                if done or step == FLAGS.max_episode_len - 1:
                    print(step)
                    for i in range(int(step / FLAGS.episode_len)):
                        self.states[epsd] = states[step - (i + 1) * FLAGS.episode_len:step - i * FLAGS.episode_len + 1]
                        self.actions[epsd] = actions[step - (i + 1) * FLAGS.episode_len:step - i * FLAGS.episode_len]
                        self.rewards[epsd] = rewards[step - (i + 1) * FLAGS.episode_len:step - i * FLAGS.episode_len]
                        epsd += 1
                        if not epsd < FLAGS.episodes:
                            self.save()
                            return
                        self.epsd_cnt[0] = epsd
                    ob = self.env.reset()
                    ob = np.concatenate((ob, ob, ob, ob), axis=-1)
                    self.save()

                    break

    def save(self):
        np.save(FLAGS.save_dir + 'states.npy', self.states)
        np.save(FLAGS.save_dir + 'actions.npy', self.actions)
        np.save(FLAGS.save_dir + 'rewards.npy', self.rewards)
        np.save(FLAGS.save_dir + 'epsd_idx.npy', self.epsd_cnt)

        print('data_saved')


def main(_):
    env_id = 'PongNoFrameskip-v4'
    a2c = A2C(inference=False)
    data_collector = Collector(env_id, a2c.make_all_environments, a2c.infer)

    data_collector.collect_data()

    data_collector.save()


if __name__ == '__main__':
    tf.app.run()

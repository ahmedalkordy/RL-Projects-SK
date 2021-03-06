import tensorflow as tf
import numpy as np
from tensorflow import keras
from tensorflow.keras import layers
from actor_critic import Actor, Critic, AC_Agent, OUActionNoise


# required for reproducing the result
np.random.seed(1)
tf.random.set_seed(1)


############################################
# ACTOR
##############################
class KukaActor(Actor):
    def __init__(self, state_size, action_size,
                 replacement, learning_rate,
                 upper_bound):
        super().__init__(state_size, action_size,
                         replacement, learning_rate,
                         upper_bound)

    def _build_net(self):
        # input is a stack of 1-channel YUV images
        last_init = tf.random_uniform_initializer(minval=-0.003, maxval=0.003)
        state_input = layers.Input(shape=self.state_size)
        conv_l1 = layers.Conv2D(15, kernel_size=6, strides=2,
                                padding="SAME", activation="relu")(state_input)
        max_pool1 = layers.MaxPool2D(pool_size=3, strides=2)(conv_l1)
        f1 = layers.Flatten()(max_pool1)
        l1 = layers.Dense(256, activation='relu')(f1)
        l2 = layers.Dense(256, activation='relu')(l1)
        net_out = layers.Dense(self.action_size, activation='tanh',
                               kernel_initializer=last_init)(l2)

        net_out = net_out * self.upper_bound
        model = keras.Model(state_input, net_out)
        model.summary()
        return model


###################################
class KukaCritic(Critic):
    def __init__(self, state_size, action_size, replacement,
                 learning_rate, gamma):
        super().__init__(state_size, action_size,  replacement,
                         learning_rate, gamma)

    def _build_net(self):
        # state input is a stack of 1-D YUV images
        state_input = layers.Input(shape=self.state_size)
        conv_l1 = layers.Conv2D(15, kernel_size=6, strides=2,
                                padding="SAME", activation="relu")(state_input)
        max_pool1 = layers.MaxPool2D(pool_size=3, strides=2)(conv_l1)
        f1 = layers.Flatten()(max_pool1)

        state_out = layers.Dense(16, activation="relu")(f1)
        state_out = layers.Dense(32, activation="relu")(state_out)

        # Action as input
        action_input = layers.Input(shape=(self.action_size,))
        action_out = layers.Dense(32, activation="relu")(action_input)

        # Both are passed through separate layer before concatenating
        concat = layers.Concatenate()([state_out, action_out])

        out = layers.Dense(256, activation="relu")(concat)
        out = layers.Dense(256, activation="relu")(out)
        net_out = layers.Dense(1)(out)

        # Outputs single value for give state-action
        model = tf.keras.Model(inputs=[state_input, action_input], outputs=net_out)
        model.summary()
        return model


class KukaACAgent(AC_Agent):
    def __init__(self, state_size, action_size,
                 replacement, lr_a, lr_c,
                 batch_size,
                 memory_capacity,
                 gamma,
                 upper_bound, lower_bound):
        self.state_size = state_size
        self.action_size = action_size
        self.replacement = replacement
        self.actor_lr = lr_a
        self.critic_lr = lr_c
        self.batch_size = batch_size
        self.memory_capacity = memory_capacity
        self.gamma = gamma
        self.upper_bound = upper_bound
        self.lower_bound = lower_bound

        self.actor = KukaActor(self.state_size, self.action_size, self.replacement,
                           self.actor_lr, self.upper_bound)
        self.critic = KukaCritic(self.state_size, self.action_size, self.replacement,
                             self.critic_lr, self.gamma)
        self.buffer = Buffer(self.state_size, self.action_size,
                             self.memory_capacity, self.batch_size)

        std_dev = 0.2
        self.noise_object = OUActionNoise(mean=np.zeros(1), std_deviation=float(std_dev) * np.ones(1))

        # Initially make weights for target and model equal
        self.actor.target.set_weights(self.actor.model.get_weights())
        self.critic.target.set_weights(self.critic.model.get_weights())



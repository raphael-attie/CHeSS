import os
import data
import model
import tensorflow as tf
import matplotlib.pyplot as plt


# -------- Setup training/validation/test data -------------#

# Data relative paths:
dataset_path = 'people_segmentation' # parent directory of images and masks directories
input_shape = (256, 256, 3)  # image size and nb of channels
batch_size = 8  # Note that we will use an infinitely repeating data generator

# Generate training/validation/test data
(train_x, train_y), (test_x, test_y) = data.get_dataset_paths(dataset_path)
train_dataset = data.create_dataset(train_x, train_y, batch=batch_size)
test_dataset = data.create_dataset(test_x, test_y, batch=batch_size)
print(f"Train: {len(train_dataset)}")
print(f"Test: {len(test_dataset)}")


# -------------------------------------------------------------------------------- #
# ------------------------- Define the U-Net ------------------------------------- #
# -------------------------------------------------------------------------------- #
checkpoint_dir = 'checkpoints'
checkpoint_name = f'final_checkpoint.ckpt'  # file containing the trained weights after last epoch
# Use pretrained weights if needed. Set to None to train from scratch
pretrained_weights = None  # tf.train.latest_checkpoint(checkpoint_dir)

n_classes = 1   # Number of classes. If binary, set n_classes to 1, used as the number of filters for the last layer

# set the filters in the convolution before max pooling for as many encoder mini blocks as needed:
# [(nb of layers before each max pooling, nb of filters in those layers), ...]
# The last encoder mini block is the bridge; it does not use max pooling
down_layer_filters = [
    (2, 64),    # 256 -> 128
    (2, 128),   # 128 -> 64
    (2, 256),   # 64 -> 32
    (2, 512),   # 32 -> 16
    (2, 1024),  # No max pooling: 16 -> 16
]
# Max pooling set as True/False, each element applies to each mini block of the encoder
# You must have as many element as in the downsamping filter list above
max_pools = (True, True, True, True, False)

ksize = 3           # Kernel size for the convolution blocks
kinit = 'HeNormal'  # Kernel initializer
batch_norm = True   # Toggle Batch Normalization
activation = True   # Toggle activation in each block
res_block = False   # Toggle ResNet block
transpose_conv = False  # Set whether to use Transpose conv. instead of Upsampling + conv

# Training parameters #
# As we use a generator with random augmentation, train lengths and batch size are not constraining the
# the number of steps per epochs and validation steps. Nonetheless, pick reasonable numbers to avoid overtraining
# given that there are only 30 samples in the data source that are very similar to each other.
epochs = 10
steps_per_epochs = len(train_x)//batch_size
# validation steps to perform at the end of each epoch:
# with the dataset generator, must be set to avoid an infinite evaluation loop after each training epoch
validation_steps = len(test_x)//batch_size


# Optimizer parameters #
learning_rate = 1e-3    # This is the default value for the 'Adam' optimizer
compiler_dict = dict(
    optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
    loss=tf.keras.losses.BinaryCrossentropy(from_logits=not activation),
    metrics=['accuracy']
)

# Instantiate the model, fit and save weights#
unet = model.unet_model(input_shape, n_classes, down_layer_filters, compiler_dict,
                        ksize=3,
                        batch_norm=batch_norm,
                        max_pools=max_pools,
                        kinit=kinit,
                        activation=activation,
                        res_block=res_block,
                        transpose_conv=transpose_conv)


if pretrained_weights is not None:
    unet.load_weights(pretrained_weights)

history = unet.fit(train_dataset,
                   epochs=epochs,
                   steps_per_epoch=steps_per_epochs,
                   validation_data=test_dataset,
                   validation_steps=validation_steps)

checkpoint_path = os.path.join(checkpoint_dir, checkpoint_name)
unet.save_weights(checkpoint_path)


# plot training and validation accuracy
plt.figure(figsize=(8, 8))
plt.plot(history.history['accuracy'], label='accuracy')
plt.plot(history.history['val_accuracy'], label='val_accuracy')
plt.xlabel('Epoch')
plt.ylabel('Accuracy')
plt.ylim([0.5, 1])
plt.legend(loc='lower right')
plt.savefig(f'U-Net_accuracies.png')



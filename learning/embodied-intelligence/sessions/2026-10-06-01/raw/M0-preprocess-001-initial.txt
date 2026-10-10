y = prepare_video(camera)    # [2,3,6,64,64]
frame = x[1, :, 4, :, :]     # [3,64,64]
rgb = frame[:, 11, 21]       # [3]
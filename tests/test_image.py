from matplotlib import cm, pyplot as plt
import numpy as np
import pymmcore_nano as pmn


def test_image(demo_core: pmn.CMMCore):
    demo_core.setProperty("Camera", "PixelType", "32bitRGB")
    demo_core.setProperty("Camera", "Mode", "Color Test Pattern")
    demo_core.snapImage()
    img = demo_core.getImage()

    print(img.dtype, img.shape, img.min(), img.max())
    plt.imshow(img, cmap='gray')
    plt.show()

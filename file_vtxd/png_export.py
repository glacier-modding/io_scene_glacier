import sys
import math
from format import VertexData

sys.path.append("..\\")
import io_binary
from PIL import Image

width = 400
height = 300

if len(sys.argv) == 2:
    path = sys.argv[1]

    resource = VertexData()
    br = io_binary.BinaryReader(open(path, 'rb'))
    resource.read(br)
    br.close()

    img_idx = 0
    for sub_mesh in resource.sub_meshes:

        height = int(math.sqrt(int(sub_mesh.num_vertices())))
        width = int(math.sqrt(int(sub_mesh.num_vertices())))
        img = Image.new(mode="RGBA", size=(width, height))

        for Y in range(height):
            for X in range(width):
                col = sub_mesh.vertexColors[(Y * width) + X]
                img.putpixel((Y, X), (col[0], col[1], col[2], col[3]))
        img.save(path + ".exported" + str(img_idx))
        img_idx += 1


else:
    print('Usage: python(3) bmp_export.py <path to VTXD file>')

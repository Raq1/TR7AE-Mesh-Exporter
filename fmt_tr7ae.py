# ================================================================================
# Tomb Raider Legend/Anniversary (PC, PS3)
# v1.97 (11 March 2023)
# Model importer by Dave
# Model exporter by Raq
# Texture exported by TheIndra
# BGObjects importer by TheIndra
# Thanks to Gh0stblade, akderebur, Joschka, TheIndra, AesirHod, alphaZomega for providing valuable information for this script
# ================================================================================


from inc_noesis import *
import math
import re
import copy

SECTION_TEXTURE = 5

def registerNoesisTypes():

    def addOptions(handle):
        noesis.addOption(handle, "-noguns", "Remove the holstered guns attachment", 0)
        noesis.addOption(handle, "-noshotgun", "Remove the holstered shotgun attachment", 0)
        noesis.addOption(handle, "-nogear", "Remove all the gear attachments (grapple hook excluded)", 0)
        return handle

    handle = noesis.register("TR7AE BGObjects (PC)", ".drm")
    noesis.setHandlerTypeCheck(handle, checkType)
    noesis.setHandlerLoadModel(handle, loadLevel)

    handle = noesis.register("TR7AE DRM (PC)",".drm")
    noesis.setHandlerTypeCheck(handle, bcCheckType)
    noesis.setHandlerLoadModel(handle, bcLoadModel)
    
    handle = noesis.register("TR7AE Mesh (PC)",".tr7aemesh")
    noesis.setHandlerTypeCheck(handle, bdCheckType)
    noesis.setHandlerLoadModel(handle, bdLoadModel)
    noesis.setHandlerWriteModel(handle, meshWriteModel)
    addOptions(handle)

    handle = noesis.register("TR7AE Texture (PC)", ".pcd")
    noesis.setHandlerTypeCheck(handle, pcdCheckType)
    noesis.setHandlerLoadRGBA(handle, pcdLoadDDS)
    noesis.setHandlerWriteRGBA(handle, pcdWriteRGBA)
    
    handle = noesis.register("TR7AE Texture (PS3)", ".pcd")
    noesis.setHandlerLoadRGBA(handle, ps3pcdLoadDDS)
    
    handle = noesis.register("TR7AE RAW (PC)", ".raw")
    noesis.setHandlerTypeCheck(handle, rawCheckType)
    noesis.setHandlerLoadRGBA(handle, rawLoadDDS)
    noesis.setHandlerWriteRGBA(handle, rawWriteRGBA)
    
    handle = noesis.register("TR7AE Raw Texture (PS3)", ".raw")
    noesis.setHandlerTypeCheck(handle, ps3rawCheckType)
    noesis.setHandlerLoadRGBA(handle, ps3rawLoadDDS)
    
    return 1


def bcCheckType(data):
    bs = NoeBitStream(data)
    file_id = bs.readUInt()

    if file_id != 0x0000000e:
        print("Invalid file")
        return 0
    else:
        return 1


# Read the model data

def bcLoadModel(data, mdlList):
    bs = NoeBitStream(data)

    tex_list, mat_list = ReadTextures(bs)


# Read DRM files

    bs.seek(4)
    entries = bs.readUInt()
    data_start = (entries * 0x14) + 8
    flag = 0

    for a in range(entries):
        bs.seek(a * 0x14 + 8)
        size1 = bs.readUInt()
        entry_type = bs.readUInt()
        bs.readUByte()
        item_entries = bs.readUShort()
        bs.readUByte()
        entry_id = bs.readUInt()

        if entry_type == 0:
            header2 = data_start + (item_entries * 8)
            bs.seek(header2)
            tr7aemesh_id = bs.readUInt()

            if tr7aemesh_id == 0x04c20453:						# mesh data found
                DrawModel(bs, header2, tex_list, mat_list, mdlList)
                flag = 1
#				break							# enable this line to just display first model found

        data_start += size1 + (item_entries * 8)


    if flag == 0:
        print("No meshes found")
        return 0


    return 1



def ReadTextures(bs):
    bs.seek(4)
    entries = bs.readUInt()
    data_start = (entries * 0x14) + 8

    tex_list = []
    mat_list = []

    for a in range(entries):
        bs.seek(a * 0x14 + 8)
        size1 = bs.readUInt()
        entry_type = bs.readUInt()
        bs.readUByte()
        item_entries = bs.readUShort()
        bs.readUByte()
        entry_id = bs.readUInt()

        if entry_type == 5:												# PCD
            material = NoeMaterial("Material_" + str(entry_id), "")
            bs.seek(data_start + 4)
            pcd_type = bs.readUInt()
            pcd_size = bs.readUInt()
            bs.readUInt()
            width = bs.readUShort()
            height = bs.readUShort()

            bs.seek(data_start + 0x18)
            raw_data = bs.readBytes(pcd_size)

            if pcd_type == 0x15:										# RGBA32
                tex1 = NoeTexture("Texture_" + str(entry_id) + ".tga", width, height, raw_data, noesis.NOESISTEX_RGBA32)

            elif pcd_type == 0x31545844:										# DXT1
                tex1 = NoeTexture("Texture_" + str(entry_id) + ".tga", width, height, raw_data, noesis.NOESISTEX_DXT1)

            elif pcd_type == 0x35545844:										# DXT5
                tex1 = NoeTexture("Texture_" + str(entry_id) + ".tga", width, height, raw_data, noesis.NOESISTEX_DXT5)

            else:
                print("Texture format ", hex(pcd_type), " unknown")

            material.setTexture("Texture_" + str(entry_id))
            tex_list.append(tex1)
            mat_list.append(material)

        data_start += size1 + (item_entries * 8)

    return tex_list, mat_list


# Draw one complete model

def DrawModel(bs, header2, tex_list, mat_list, mdlList):
    ctx = rapi.rpgCreateContext()
    bs.seek(header2)
    file_id = bs.readUInt()

    bone_count1 = bs.readUInt()
    bone_count2 = bs.readUInt()
    bone_data = bs.readUInt() + header2
    scaleX = bs.readFloat()
    scaleY = bs.readFloat()
    scaleZ = bs.readFloat()


# Read skeleton data

    bones = []
    bonesM = []

    for a in range(bone_count1):
        bs.seek(bone_data + (a * 0x40) + 0x20)

        pos = NoeVec3.fromBytes(bs.readBytes(12))
        bs.seek(12, NOESEEK_REL)
        boneParent = bs.readUInt()

        # Read HInfo data

        HInfo = bs.readUInt()
        if HInfo != 0:

            bs.seek(HInfo + header2)
            numHSpheres = bs.readInt()
            hsphereList = bs.readUInt()
            numHBoxes = bs.readInt()
            hboxList = bs.readUInt()
            numHMarkers = bs.readInt()
            hmarkerList = bs.readUInt()
            numHCapsules = bs.readInt()
            hcapsuleList = bs.readUInt()

            print("\nHInfo detected for bone%03i"%a + "\nHSpheres = " + str(numHSpheres) + "\nHBoxes = " + str(numHBoxes) + "\nHMarkers = " + str(numHMarkers) + "\nHCapsules = " + str(numHCapsules))

            if numHSpheres > 0:
                bs.seek (hsphereList + header2)
                flags = bs.readShort()
                id = bs.readByte()
                rank = bs.readByte()
                radius = bs.readShort()
                X = bs.readShort()
                Y = bs.readShort()
                Z = bs.readShort()
                radiusSquares = bs.readUInt()
                mass = bs.readUInt()
                buoyancyFactor = bs.readByte()
                explosionFactor = bs.readByte()
                iHitMaterialType = bs.readByte()
                pad = bs.readByte()
                damage = bs.readShort()

            if numHMarkers > 0:
                bs.seek (hmarkerList + header2)
                for b in range(numHMarkers):
                    bone = bs.readInt()
                    index = bs.readInt()
                    posMarker = NoeVec3.fromBytes(bs.readBytes(12))
                    rx = bs.readFloat()
                    ry = bs.readFloat()
                    rz = bs.readFloat()
                    matrixMarker = NoeQuat([0, 0, 0, 1]).toMat43()   
                    matrixMarker[3] = posMarker
                    if not a:
                        matrixMarker *= NoeAngles([90,0,0]).toMat43()

                        bonesM.append(NoeBone(a, "Marker%03i"%a, matrixMarker, None, bone))

                    print("posMarker being " + str(posMarker))

        matrix = NoeQuat([0, 0, 0, 1]).toMat43()
        matrix[3] = pos
        if not a:
            matrix *= NoeAngles([90,0,0]).toMat43()

        bones.append(NoeBone(a, "bone%03i"%a, matrix, None, boneParent))

    bones = rapi.multiplyBones(bones)
    bonesM = rapi.multiplyBones(bones)


# Read vertex data

    bs.seek(header2 + 0x20)
    vert_count = bs.readUInt()
    vert_start = bs.readUInt() + header2

    bs.seek(header2 + 0x58)
    face_info = bs.readUInt() + header2

    vertices = bytearray(vert_count * 12)
    uvs = bytearray(vert_count * 8)
    normals = bytearray(vert_count * 12)
    bone_idx = bytearray(vert_count * 4)
    weights = bytearray(vert_count * 8)

    bs.seek(vert_start)

    for v in range(vert_count):
        bs.seek(vert_start + (v * 0x10))
        vx = bs.readShort() * scaleX
        vy = bs.readShort() * scaleY
        vz = bs.readShort() * scaleZ

        nx = bs.readByte() / 127
        ny = bs.readByte() / 127
        nz = bs.readByte() / 127
        bs.readByte()								# padding byte

        bone_id = bs.readUShort()
        uvx = bs.readUShort() << 16							# convert to correct float value
        uvy = bs.readUShort() << 16

        if bone_id > (bone_count1-1):
            bs.seek(bone_data + (bone_id * 0x40) + 0x38)
            bone_id = bs.readUShort()
            bone_id2 = bs.readUShort()
            weight1 = bs.readFloat()
            weight2 = 1 - weight1
            struct.pack_into("<HH", bone_idx, v * 4, bone_id, bone_id2)
            struct.pack_into("<ff", weights, v * 8, weight2, weight1)
        else:
            struct.pack_into("<HH", bone_idx, v * 4, bone_id, 0)
            struct.pack_into("<ff", weights, v * 8, 1, 0)

# Transform vertices to bone position without using rpgSkinPreconstructedVertsToBones

        vertpos = bones[bone_id].getMatrix().transformPoint([vx, vy, vz])
        vx = vertpos[0]
        vy = vertpos[1]
        vz = vertpos[2]
        
        norm = bones[bone_id].getMatrix().transformNormal([nx, ny, nz])
        nx = norm[0]
        ny = norm[1]
        nz = norm[2]

        struct.pack_into("<fff", vertices, v * 12, vx, vy, vz)
        struct.pack_into("<II", uvs, v*8, uvx, uvy)
        struct.pack_into("<fff", normals, v*12, nx, ny, nz)

    flag = 0
    current_mesh = face_info
    mesh_num = 0

    rapi.rpgBindPositionBuffer(vertices, noesis.RPGEODATA_FLOAT, 12)
    rapi.rpgBindNormalBuffer(normals, noesis.RPGEODATA_FLOAT, 12)
    rapi.rpgBindUV1Buffer(uvs, noesis.RPGEODATA_FLOAT, 8)
    rapi.rpgBindBoneIndexBuffer(bone_idx, noesis.RPGEODATA_USHORT, 4, 2)
    rapi.rpgBindBoneWeightBuffer(weights, noesis.RPGEODATA_FLOAT, 8, 2)

    while flag == 0:
        bs.seek(current_mesh)
        face_count = bs.readUShort()

        if face_count == 0:								# no more sub-meshes
            break

        drawgroup = bs.readUShort()
        texidoffset = bs.tell()
        tex_id = bs.readUShort() & 0x1FFF						# bits 0-12
        misc3 = bs.readUShort()
        sortPush = bs.readFloat()
        scrollOffset = bs.readFloat()
        
        bs.seek(texidoffset)
        texture_id = bs.readBits(13)
        blendValue = bs.readBits(4)
        unk1 = bs.readBits(4)
        SingleSided = bs.readBits(1)
        unk2 = bs.readBits(10)
        
        bs.seek(texidoffset)
        tpageid = bs.readInt()
        sortPush = bs.readFloat()
        scrollOffset = bs.readFloat()
        
        current_mesh = bs.readUInt() + header2					# next face section
        faces = bs.readBytes(face_count * 2)
        
        rapi.rpgSetMaterial("Material_" + str(tex_id))
        rapi.rpgSetName("Mesh_" + str(mesh_num) + "_TexID_" + str(texture_id) + "_Blend_" + str(blendValue) + "_SingleSided_" + str(SingleSided) + "_dg_" + str(drawgroup))
        rapi.rpgCommitTriangles(faces, noesis.RPGEODATA_USHORT, face_count, noesis.RPGEO_TRIANGLE)
        mesh_num += 1

    try:
        mdl = rapi.rpgConstructModel()
    except:
        mdl = NoeModel()

    mdl.setModelMaterials(NoeModelMaterials(tex_list, mat_list))
    mdl.setBones(bones)
    mdlList.append(mdl)

    return 1
    
def bdCheckType(data):
    bs = NoeBitStream(data)
    file_id = bs.readUInt()

    if file_id != 0x54434553:
        print("Invalid file")
        return 0
    else:
        return 1
        
def bdLoadModel(data, mdlList):
    bs = NoeBitStream(data)
    ctx = rapi.rpgCreateContext()

    bs.seek(0x0d)
    header1_count = bs.readUByte()					# or Short?
    header2 = (header1_count * 0x8) + 0x18					# 0x5304c204

    bs.seek(header2 + 4)
    bone_count1 = bs.readUInt()
    bone_count2 = bs.readUInt()
    bone_data = bs.readUInt() + header2
    scaleX = bs.readFloat()
    scaleY = bs.readFloat()
    scaleZ = bs.readFloat()
    bs.seek(header2 + 0x4c)


# Read skeleton data

    bones = []
    secondBoneList = []
    hmarker_num = 0
    boneHMarker = 0
    hsphere_num = 0

    for a in range(bone_count1):
        bs.seek(bone_data + (a * 0x40) + 0x20)

        pos = NoeVec3.fromBytes(bs.readBytes(12))
        bs.seek(4, NOESEEK_REL)
        flags = bs.readUInt()
        bs.seek(4, NOESEEK_REL)
        boneParent = bs.readUInt()

        # Read HInfo data

        HInfo = bs.readUInt()
        if HInfo != 0:

            bs.seek(HInfo + header2)
            numHSpheres = bs.readInt()
            hsphereList = bs.readUInt()
            numHBoxes = bs.readInt()
            hboxList = bs.readUInt()
            numHMarkers = bs.readInt()
            hmarkerList = bs.readUInt()
            numHCapsules = bs.readInt()
            hcapsuleList = bs.readUInt()

            print("\nHInfo detected for bone%03i"%a + "\nHSpheres = " + str(numHSpheres) + "\nHBoxes = " + str(numHBoxes) + "\nHMarkers = " + str(numHMarkers) + "\nHCapsules = " + str(numHCapsules))

            if numHSpheres > 0:
                bs.seek (hsphereList + header2)
                for b in range(numHSpheres):
                    flags = bs.readShort()
                    id = bs.readByte()
                    rank = bs.readByte()
                    radius = bs.readShort()
                    X = bs.readShort()
                    Y = bs.readShort()
                    Z = bs.readShort()
                    radiusSquares = bs.readUInt()
                    mass = bs.readUInt()
                    buoyancyFactor = bs.readByte()
                    explosionFactor = bs.readByte()
                    iHitMaterialType = bs.readByte()
                    pad = bs.readByte()
                    damage = bs.readShort()

                    print("HSphere {} ".format(hsphere_num) + str((X, Y, Z)))

                    hsphere_num += 1

            if numHMarkers > 0:
                bs.seek (hmarkerList + header2)
                for c in range(numHMarkers):
                    bone = bs.readInt()
                    index = bs.readInt()
                    posMarker = NoeVec3.fromBytes(bs.readBytes(12))
                    rx = bs.readFloat()
                    ry = bs.readFloat()
                    rz = bs.readFloat()
                    matrixMarker = NoeQuat([0, 0, 0, 1]).toMat43()   
                    matrixMarker[3] = posMarker
                    if not c:
                        matrixMarker *= NoeAngles([90,0,0]).toMat43()

                    secondBoneList.append(NoeBone(c, "HMarker_{}_bone_{}_index_{}".format(hmarker_num, boneHMarker, index), matrixMarker, None, bone))

                    print("HMarker {} ".format(hmarker_num) + str(posMarker))
                    # bones.extend(secondBoneList)
                    # for i, bone in enumerate(bones):
                      # bone.index = i

                    hmarker_num += 1
        boneHMarker += 1

        matrix = NoeQuat([0, 0, 0, 1]).toMat43()
        matrix[3] = pos
        if not a:
            matrix *= NoeAngles([90,0,0]).toMat43()

        bones.append(NoeBone(a, "bone%03i"%a, matrix, None, boneParent))

    bones = rapi.multiplyBones(bones)


# Read vertex data

    bs.seek(header2 + 0x20)
    vert_count = bs.readInt()
    vert_start = bs.readInt() + header2

    bs.seek(header2 + 0x58)
    face_info = bs.readUInt() + header2

    vertices = bytearray(vert_count * 12)
    uvs = bytearray(vert_count * 8)
    normals = bytearray(vert_count * 12)

    bs.seek(vert_start)
    bone_idx = bytearray(vert_count * 8)
    bone_wgt = bytearray(vert_count * 16)

    bs.seek(header2 + 0x20)
    vert_count = bs.readUInt()
    vert_start = bs.readUInt() + header2

    bs.seek(header2 + 0x58)
    face_info = bs.readUInt() + header2

    vertices = bytearray(vert_count * 12)
    uvs = bytearray(vert_count * 8)
    normals = bytearray(vert_count * 12)
    bone_idx = bytearray(vert_count * 4)
    weights = bytearray(vert_count * 8)

    bs.seek(vert_start)

    for v in range(vert_count):
        bs.seek(vert_start + (v * 0x10))
        vx = bs.readShort() * scaleX
        vy = bs.readShort() * scaleY
        vz = bs.readShort() * scaleZ

        nx = bs.readByte() / 127
        ny = bs.readByte() / 127
        nz = bs.readByte() / 127
        bs.readByte()								# padding byte

        bone_id = bs.readUShort()
        uvx = bs.readUShort() << 16							# convert to correct float value
        uvy = bs.readUShort() << 16

        if bone_id > (bone_count1-1):
            bs.seek(bone_data + (bone_id * 0x40) + 0x38)
            bone_id = bs.readUShort()
            bone_id2 = bs.readUShort()
            weight1 = bs.readFloat()
            weight2 = 1 - weight1
            struct.pack_into("<HH", bone_idx, v * 4, bone_id, bone_id2)
            struct.pack_into("<ff", weights, v * 8, weight2, weight1)
        else:
            struct.pack_into("<HH", bone_idx, v * 4, bone_id, 0)
            struct.pack_into("<ff", weights, v * 8, 1, 0)


# Transform vertices to bone position without using rpgSkinPreconstructedVertsToBones

        vertpos = bones[bone_id].getMatrix().transformPoint([vx, vy, vz])
        vx = vertpos[0]
        vy = vertpos[1]
        vz = vertpos[2]
        
        norm = bones[bone_id].getMatrix().transformNormal([nx, ny, nz])
        nx = norm[0]
        ny = norm[1]
        nz = norm[2]

        struct.pack_into("<fff", vertices, v * 12, vx, vy, vz)
        struct.pack_into("<II", uvs, v*8, uvx, uvy)
        struct.pack_into("<fff", normals, v*12, nx, ny, nz)

    flag = 0
    current_mesh = face_info
    mesh_num = 0

    rapi.rpgBindPositionBuffer(vertices, noesis.RPGEODATA_FLOAT, 12)
    rapi.rpgBindNormalBuffer(normals, noesis.RPGEODATA_FLOAT, 12)
    rapi.rpgBindUV1Buffer(uvs, noesis.RPGEODATA_FLOAT, 8)
    rapi.rpgBindBoneIndexBuffer(bone_idx, noesis.RPGEODATA_USHORT, 4, 2)
    rapi.rpgBindBoneWeightBuffer(weights, noesis.RPGEODATA_FLOAT, 8, 2)

    while flag == 0:
        bs.seek(current_mesh)
        face_count = bs.readUShort()

        if face_count == 0:								# no more sub-meshes
            break

        drawgroup = bs.readUShort()
        texidoffset = bs.tell()
        tex_id = bs.readUShort() & 0x1FFF						# bits 0-12
        misc3 = bs.readUShort()
        sortPush = bs.readFloat()
        scrollOffset = bs.readFloat()
        
        bs.seek(texidoffset)
        texture_id = bs.readBits(13)
        blendValue = bs.readBits(4)
        unk1 = bs.readBits(4)
        SingleSided = bs.readBits(1)
        unk2 = bs.readBits(10)
        
        bs.seek(texidoffset)
        tpageid = bs.readInt()
        sortPush = bs.readFloat()
        scrollOffset = bs.readFloat()
        
        current_mesh = bs.readUInt() + header2					# next face section
        faces = bs.readBytes(face_count * 2)
        
        rapi.rpgSetMaterial("Material_" + str(tpageid))
        rapi.rpgSetName("Mesh_" + str(mesh_num) + "_TexID_" + str(texture_id) + "_Blend_" + str(blendValue) + "_SingleSided_" + str(SingleSided) + "_dg_" + str(drawgroup))
        rapi.rpgCommitTriangles(faces, noesis.RPGEODATA_USHORT, face_count, noesis.RPGEO_TRIANGLE)
        mesh_num += 1

# Read MFace data

    bs.seek(header2 + 0x30)
    numFaces = bs.readInt()
    faceList = bs.readInt() + header2
    for f in range(numFaces):
        if faceList > 0:
            bs.seek(faceList)
            f0 = bs.readShort()
            f1 = bs.readShort()
            f2 = bs.readShort()
            sameVertBits1 = bs.readBits(5)
            sameVertBits2 = bs.readBits(5)
            sameVertBits3 = bs.readBits(5)

    try:
        mdl = rapi.rpgConstructModel()
    except:
        mdl = NoeModel()

    mdl.setBones(bones)
    mdlList.append(mdl)

    return 1


def pcdCheckType(data):
    bs = NoeBitStream(data)
    bs.seek(0x18, NOESEEK_ABS)
    magic = bs.readUInt()
    if magic == 0x39444350:
        return 1
        
    elif magic == 0x54335350:
        return 1
        
    else: 
        print("Fatal Error: Unknown file magic: " + str(hex(magic) + " expected 0x39444350!"))
        return 1

def pcdLoadDDS(data, texList):
    bs = NoeBitStream(data)
    bs.seek(0x18, NOESEEK_ABS)
    magic = bs.readUInt()
    
    if magic == 0x54335350: # PS3T
        return ps3pcdLoadDDS(data, texList)
            
    ddsType = bs.readUInt()
    ddsSize = bs.readUInt()
    bs.seek(0x4, NOESEEK_REL)
    ddsWidth = bs.readUShort()
    ddsHeight = bs.readUShort()
    ddsFlags = bs.readByte()
    ddsMipCount = bs.readByte()
    ddsType2 = bs.readUShort()
    ddsData = bs.readBytes(ddsSize)
    ddsFmt = None
    if ddsType == 0x31545844:
        ddsFmt = noesis.NOESISTEX_DXT1
    elif ddsType == 0x35545844:
        ddsFmt = noesis.NOESISTEX_DXT5
    elif ddsType == 0x15:
        ddsData = rapi.imageDecodeRaw(ddsData, ddsWidth, ddsHeight, "a8a8a8a8")
        ddsFmt = noesis.NOESISTEX_RGBA32
    else: 
        print("Fatal Error: " + "Unknown DDS type: " + str(hex(ddsType)) + " using default DXT1")
    texList.append(NoeTexture("Texture", ddsWidth, ddsHeight, ddsData, ddsFmt))
    return 1

def pcdWriteRGBA(data, width, height, bs):
    filename = rapi.getOutputName()
    oldDDS = rapi.loadIntoByteArray(rapi.getInputName())
    og = NoeBitStream(oldDDS)
    fsize = os.path.getsize(rapi.getInputName()) - 128

    # Check if input file is a DDS file
    ddsMagic = og.readUInt()
    if ddsMagic != 542327876:
            print ("\nInput file is not a DDS file!\nAborting...\n")
            return 0

    # extract id from filename
    headerSize = 48
    split = re.findall("[0-9]+_([0-9a-f]+)", filename)[-1]
    id = int(split, 16)

    print("ID detected from filename as " + str(id))

    # set format values based on options
    formatMagic = None
    format = None

    og.seek(84, NOESEEK_ABS)
    ddsType = og.readUInt()
    if ddsType == 827611204: #DXT1
        formatMagic = "DXT1"
        format = noesis.NOE_ENCODEDXT_BC1
    elif ddsType == 894720068: #DXT5
        formatMagic = "DXT5"
        format = noesis.NOE_ENCODEDXT_BC3

    # write section header
    bs.writeString("SECT", False)	# cdcEngineTools section magic
    bs.writeUInt(0)                 # size - will be written later
    bs.writeByte(SECTION_TEXTURE)   # section type
    bs.writeByte(0)                 # padding
    bs.writeUShort(0)               # version id
    bs.writeUInt(0)                 # packedData
    bs.writeUInt(id)                # section id
    bs.writeUInt(0xFFFFFFFF)        # specialisation mask

    # write texture header
    bs.writeString("PCD9", False)       # magic number
    bs.writeString(formatMagic, False)  # format
    bs.writeUInt(0)                     # image size - will be written later
    bs.writeUInt(0)                     # palette size
    bs.writeUShort(width)               # width
    bs.writeUShort(height)              # height
    bs.writeUByte(0)                    # depth
    bs.writeUByte(0)                    # number of mipmaps
    bs.writeUShort(3)                   # flags - always 3 on any DXT1/DXT5 texture. 0 in the case of PCD file with no DXT format specified. Maybe will try to deal with it someday, maybe not.

    print("Image is {}x{}".format(width, height))

    # write image data
    dxtData = rapi.imageEncodeDXT(data, 4, width, height, format)
    og.seek(128, NOESEEK_ABS)
    bs.writeBytes(og.readBytes(fsize))

    # write mipmaps, mostly copied from old exporter
    mipWidth = int(width >> 1) 
    mipHeight = int(height >> 1)
    numMipmaps = 0

    while mipWidth >= 1 and mipHeight >= 1:
        print("Mipmap {}x{}".format(mipWidth, mipHeight))

        # resample and encode to format
        mipData = rapi.imageResample(data, width, height, mipWidth, mipHeight)
        dxtData = rapi.imageEncodeDXT(mipData, 4, mipWidth, mipHeight, format)

        bs.writeBytes(dxtData)

        numMipmaps += 1

        # next mipmap size
        mipWidth = int(mipWidth >> 1)
        mipHeight = int(mipHeight >> 1)

    size = bs.tell()

    # correct section size
    bs.seek(4, NOESEEK_ABS)
    bs.writeUInt(size - 24)

    # correct image size
    bs.seek(32, NOESEEK_ABS)
    bs.writeUInt(size - 48)

    # correct number of mipmaps, could be calculated above but meh
    bs.seek(45, NOESEEK_ABS)
    bs.writeUByte(numMipmaps)
    
    print("Written {} bytes to file".format(size))

    return 1
    
    
def ps3pcdLoadDDS(data, texList):
    bs = NoeBitStream(data, 1)
    bs.seek(0x18, NOESEEK_ABS)
    magic = bs.readUInt()
    ddsSize = bs.readUInt()
    bs.seek(0x24, NOESEEK_ABS)
    ddsType = bs.readByte()
    bs.seek(0x2C, NOESEEK_ABS)
    ddsWidth = bs.readUShort()
    ddsHeight = bs.readUShort()
    bs.seek(0x3C, NOESEEK_ABS)
    ddsData = bs.readBytes(ddsSize)
    ddsFmt = None
    if ddsType == -0x7a:
        ddsFmt = noesis.NOESISTEX_DXT1
    elif ddsType == -0x78:
        ddsFmt = noesis.NOESISTEX_DXT5
    elif ddsType == 0x15:
        ddsData = rapi.imageDecodeRaw(ddsData, ddsWidth, ddsHeight, "a8a8a8a8")
        ddsFmt = noesis.NOESISTEX_RGBA32
    else: 
        print("Fatal Error: " + "Unknown DDS type: " + str(hex(ddsType)) + " using default DXT1")
    texList.append(NoeTexture("Texture", ddsWidth, ddsHeight, ddsData, ddsFmt))

    return 1
    
def rawCheckType(data):
    bs = NoeBitStream(data)
    magic = bs.readUInt()
    pixelDataStart = bs.readUInt()
    if pixelDataStart == 0x00000080:
        return 1
    else: 
        print("Fatal Error: Unknown file magic: " + str(hex(magic) + " expected 0x52415721!"))
        return 0

def rawLoadDDS(data, texList):
    bs = NoeBitStream(data)
    magic = bs.readUInt()
    bs.seek(0x8, NOESEEK_ABS)
    ddsSize = bs.readUInt()
    bs.seek(0x14, NOESEEK_ABS)
    ddsWidth = bs.readInt()
    bs.seek(0x18, NOESEEK_ABS)
    ddsHeight = bs.readInt()
    bs.seek(0x80, NOESEEK_ABS)
    ddsData = bs.readBytes(ddsSize)
    ddsData = rapi.imageDecodeRaw(ddsData, ddsWidth, ddsHeight, "b8g8r8a8")
    texList.append(NoeTexture("Texture", ddsWidth, ddsHeight, ddsData))
    return 1
    
def rawWriteRGBA(data, width, height, bs):
    brawAsSource = False
    
    def getExportName(fileName):		
        if fileName == None:
            newrawName = rapi.getInputName()
        else:
            newrawName = fileName
        newrawName =  newrawName.lower().replace(".rawout","").replace(".raw","").replace(".dds","").replace("out.",".").replace(".jpg","").replace(".png","").replace(".tga","").replace(".gif","")
        newrawName = noesis.userPrompt(noesis.NOEUSERVAL_FILEPATH, "Export over raw", "Choose a raw file to export over", newrawName + ".raw", None)
        if newrawName == None:
            print("Aborting...")
            return
        return newrawName
        
    fileName = None
    newrawName = getExportName(fileName)
    if newrawName == None:
        return 0
    while not (rapi.checkFileExists(newrawName)):
        print ("File not found")
        newrawName = getExportName(fileName)	
        fileName = newrawName
        if newrawName == None:
            return 0		
            
    newraw = rapi.loadIntoByteArray(newrawName)
    oldDDS = rapi.loadIntoByteArray(rapi.getInputName())
    f = NoeBitStream(newraw)
    og = NoeBitStream(oldDDS)
    
    magic = f.readUInt()
    ddsMagic = og.readUInt()
    if magic != 0x52415721:
        print ("Selected file is not a raw file!\nAborting...")
        return 0
    else:
        if ddsMagic == 0x52415721:
            brawAsSource = True
            headerSize = 128
        else:
            print ("Input file is not a supported format or a raw file\nEncoding...")
    
    #copy header
    f.seek(0, NOESEEK_ABS)
    bs.writeBytes(f.readBytes(128))
    
    #write image data	
    mipWidth = width
    mipHeight = height
    
    print ("Writing Image Data at:", bs.tell())
    while mipWidth >= 1 and mipHeight >= 1:
        mipData = rapi.imageResample(data, width, height, mipWidth, mipHeight)
        dxtData = rapi.imageEncodeRaw(mipData, mipWidth, mipHeight, "b8g8r8a8")
        bs.writeBytes(dxtData)
        
        if mipWidth == 1 and mipHeight == 1:
            break
        if mipWidth > 1:
            mipWidth = int(mipWidth / 2)
        if mipHeight > 1:
            mipHeight = int(mipHeight / 2)
            
    imgSize = bs.tell() - 128
    #adjust header
    bs.seek(0x8, NOESEEK_ABS)
    bs.writeInt(imgSize)
    bs.seek(0x8, NOESEEK_REL)
    bs.writeInt(width)
    bs.writeInt(height)
    
    return 1

def ps3rawCheckType(data):
    bs = NoeBitStream(data)
    magic = bs.readUInt()
    pixelDataStart = bs.readUInt()
    if pixelDataStart == 0x80000000:
        return 1
    else: 
        print("Fatal Error: Unknown file magic: " + str(hex(magic) + " expected 0x52415721!"))
        return 0

def ps3rawLoadDDS(data, texList):
    bs = NoeBitStream(data, 1)
    magic = bs.readUInt()
    bs.seek(0x8, NOESEEK_ABS)
    ddsSize = bs.readUInt()
    bs.seek(0x14, NOESEEK_ABS)
    ddsWidth = bs.readInt()
    bs.seek(0x18, NOESEEK_ABS)
    ddsHeight = bs.readInt()
    bs.seek(0x80, NOESEEK_ABS)
    ddsData = bs.readBytes(ddsSize)
    untwid = bytearray()
    for x in range(0, ddsHeight):
        for y in range(0, ddsWidth):
            idx = noesis.morton2D(x, y)
            untwid += ddsData[idx*4:idx*4+4]
    ddsData = rapi.imageDecodeRaw(untwid, ddsWidth, ddsHeight, "a8r8g8b8")
    texList.append(NoeTexture("Texture", ddsWidth, ddsHeight, ddsData))
    return 1

#BGObject

def checkType(data):
    bs = NoeBitStream(data)
    
    if bs.readUInt() != 14:
        trace("Invalid DRM version")
        return 0
        
    bs.seek(0, NOESEEK_ABS)
    drm = SectionList(bs)
    
    # skip to first section to read Level structure
    section = drm.sections[0]
    bs.seek(section.offset, NOESEEK_ABS)
    
    # skip to versionNumber
    bs.seek(0xA8, NOESEEK_REL)
    versionNumber = bs.readUInt()
    
    if versionNumber != 79824059:
        trace("DRM does not have level versionNumber")
        return 0
    
    trace("DRM is a level")
    return 1
    
def loadLevel(data, mdlList):
    bs = NoeBitStream(data)
    ctx = rapi.rpgCreateContext()
    
    drm = SectionList(bs, True)
    
    # first section, level structure
    section = drm.sections[0]
    bs.seek(section.offset, NOESEEK_ABS)
    
    ptr = drm.pointerHere(bs, section)
    if ptr == None:
        print("Failed to read terrain, was nullptr")
        return 0
        
    bs.seek(ptr.offset, NOESEEK_ABS)
    
    return readTerrain(bs, drm, ptr.section, mdlList)
    
def readTerrain(bs, drm, section, mdlList):
    # terrain structure, skip to 0x30 for bgobject members
    bs.seek(0x30, NOESEEK_REL)
    
    numBGObjects = bs.readUInt()
    print(str(numBGObjects) + " BGObjects in terrain")
    
    ptr = drm.pointerHere(bs, section)
    if ptr == None:
        print("Level has no BGObjects")
        return 0
        
    bs.seek(ptr.offset, NOESEEK_ABS)
    
    return readBGObjectList(bs, drm, ptr.section, numBGObjects, mdlList)
    
def readBGObjectList(bs, drm, section, numBGObjects, mdlList):
    # go trough all bg objects
    for i in range(numBGObjects):
        scaleX = bs.readFloat()
        scaleY = bs.readFloat()
        scaleZ = bs.readFloat()
    
        # read the vertexCount and seek back
        bs.seek(0x3C, NOESEEK_REL)
        vertexCount = bs.readUInt()
        bs.seek(-8, NOESEEK_REL)
        
        trace(str(vertexCount) + " vertexCount for bgobject " + str(i))
        
        oldOffset = bs.tell()
        
        # seek to vertex list
        ptr = drm.pointerHere(bs, section)
        if ptr == None:
            print("No vertex list")
            return 0
            
        bs.seek(ptr.offset, NOESEEK_ABS)
        
        vertices = bytearray(vertexCount * 12)
        uvs = bytearray(vertexCount * 8)
        
        for v in range(vertexCount):
            x = -(bs.readShort() * scaleX)
            z = bs.readShort() * scaleY
            y = bs.readShort() * scaleZ
            
            bs.seek(2, NOESEEK_REL)
            
            uvx = bs.readShort() * 0.00024414062
            uvy = bs.readShort() * 0.00024414062
            
            struct.pack_into("<fff", vertices, v * 12, x, y, z)
            struct.pack_into("<ff", uvs, v * 8, uvx, uvy)
            
        rapi.rpgBindPositionBuffer(vertices, noesis.RPGEODATA_FLOAT, 12)
        rapi.rpgBindUV1Buffer(uvs, noesis.RPGEODATA_FLOAT, 8)
        
        # seek back and seek to strip info
        bs.seek(oldOffset - 0x14, NOESEEK_ABS)
        
        strip = drm.pointerHere(bs, section)
        oldOffset = bs.tell()
        
        # follow texture strip
        readTextureStrip(bs, drm, strip)
        
        # return to original position and skip to end of this BGobject
        bs.seek(oldOffset + 0x2C, NOESEEK_ABS)	
        
        mdl = rapi.rpgConstructModel()
        mdl.setModelMaterials(NoeModelMaterials(drm.textures, drm.materials))
        
        rapi.rpgClearBufferBinds()
        rapi.rpgReset()
        
        mdlList.append(mdl)
        
    # done?
    return 1
    
def readTextureStrip(bs, drm, ptr):
    bs.seek(ptr.offset, NOESEEK_ABS)
    
    numVertices = bs.readUInt()
    
    trace(str(numVertices) + " vertices")
    
    if numVertices == 0:
        return
    
    bs.seek(8, NOESEEK_REL)
    tpageid = bs.readUInt() & 0x1FFF
    
    trace("tpageid " + str(tpageid))
    
    bs.seek(8, NOESEEK_REL)
    
    # read ptr, then after read the vertice list
    ptr = drm.pointerHere(bs, ptr.section)
    
    indices = bs.readBytes(numVertices * 2)
    
    rapi.rpgSetMaterial("Material_" + str(tpageid))
    rapi.rpgCommitTriangles(indices, noesis.RPGEODATA_USHORT, numVertices, noesis.RPGEO_TRIANGLE, 1)
    
    if ptr == None:
        trace("strip ptr is nullptr")
        return
        
    readTextureStrip(bs, drm, ptr)

def trace(str):
    if False: # set to True for logging
        print(str)

# based on https://github.com/TheIndra55/TR7AE-level-viewer/blob/main/src/Section.ts
class SectionList:
    bs = None
    sections = None
    
    # Noesis specific
    materials = []
    textures = []
    
    def __init__(self, bs, loadTextures = False):
        self.bs = bs
        self.sections = []
        
        version = bs.readUInt()
        numSections = bs.readUInt()
        
        trace("version " + str(version) + " numSections " + str(numSections))
        
        for i in range(numSections):
            section = self.readSection()
            self.sections.append(section)

            #trace("section {}, size {}".format(i, section.size))
        
        for section in self.sections:
            section.readRelocations(bs)
            
            # seek cursor to end of section to read next relocations
            bs.seek(section.size, NOESEEK_REL)
            
            # is it a texture?
            if section.type == 5 and loadTextures: # SectionType.Texture
                self.readTexture(bs, section)
    
    def readSection(self):
        bs = self.bs
    
        size = bs.readUInt()
        type = bs.readByte()
        bs.seek(3, NOESEEK_REL)
        
        packedData = bs.readUInt()
        id = bs.readUInt()
        bs.seek(4, NOESEEK_REL)
        
        section = Section(size, type, packedData >> 8, id)
        return section

    # reads an offset, gets the associated relocation and follows it. 
    def pointerHere(self, bs, section):
        offset = bs.tell() - section.offset
        
        #trace(str(offset) + " < ptr")
        
        relocation = section.findRelocation(offset)
        
        if relocation == None:
            # move cursor and return nullptr
            bs.seek(4, NOESEEK_REL)             
            return None
            
        target = self.sections[relocation.section]
        pointer = Pointer(target, target.offset + bs.readUInt())
        
        return pointer
        
    def readTexture(self, bs, section):
        oldOffset = bs.tell() # so we can reset the cursor after
        bs.seek(section.offset, NOESEEK_ABS)
        
        material = NoeMaterial("Material_" + str(section.id), "")
        bs.seek(4, NOESEEK_REL)
        
        format = bs.readUInt()
        bitmapSize = bs.readUInt()
        bs.seek(4, NOESEEK_REL)
        width = bs.readUShort()
        height = bs.readUShort()
        
        # seek to texture data
        bs.seek(4, NOESEEK_REL)
        data = bs.readBytes(bitmapSize)
        
        bs.seek(oldOffset, NOESEEK_ABS)
        
        texture = None
        if format == 0x31545844: # DXT1
            texture = NoeTexture("Texture_" + str(section.id), width, height, data, noesis.NOESISTEX_DXT1)
        elif format == 0x35545844: # DXT5
            texture = NoeTexture("Texture_" + str(section.id), width, height, data, noesis.NOESISTEX_DXT5)
        else:
            trace("section {} has texture with format {}".format(section.id, format))
            return
            
        material.setTexture("Texture_" + str(section.id))
        
        self.materials.append(material)
        self.textures.append(texture)
        
class Section:
    size = None
    type = None
    numRelocations = None
    id = None
    
    relocations = None
    
    # offset in the file where the section data starts (after relocations)
    offset = None
    
    def __init__(self, size, type, numRelocations, id):
        self.size = size
        self.type = type
        self.numRelocations = numRelocations
        self.id = id
        self.relocations = []
        
    def readRelocations(self, bs):
        for i in range(self.numRelocations):
            typeAndSectionInfo = bs.readShort()
            bs.seek(2, NOESEEK_REL)
            
            relocation = Relocation()
            relocation.section = typeAndSectionInfo >> 3
            relocation.offset = bs.readUInt()
            
            #trace("{} {} {}".format(relocation.section, relocation.offset, bs.tell()))
            
            self.relocations.append(relocation)
            
        self.offset = bs.tell()
        
    def findRelocation(self, offset):
        found = None
        
        for relocation in self.relocations:
            if relocation.offset == offset:
                found = relocation
        
        return found 
        
class Relocation:
    section = None
    offset = None

class Pointer:
    section = None
    offset = None
    
    def __init__(self, section, offset):
        self.section = section
        self.offset = offset

#tr7aemesh mesh exporter by Raq
#In case you're wondering, no, I'm not good at this. I barely know what I'm doing. This code is a huge mess.
def meshWriteModel(mdl, bs):
    filename = rapi.getOutputName()

    # check if model exceeds vertex limit

    numVerts = 0

    for m, mesh in enumerate(mdl.meshes):
        numVerts += len(mesh.positions)

        if numVerts > 21850:
            print ("\nERROR: This model exceeds the limit of 21850 vertices")
            return 0

    # check if model has any vertex exceeding 2 weights

    for m, mesh in enumerate(mdl.meshes):
        f = []
        for vertIdx,skinVert in enumerate(mesh.weights):

            if len(skinVert.indices) > 2:
                print ("\nERROR: This model contains vertices with more than 2 weights")
                return 0

    # extract id from filename
    split = re.split("[\\\\_.]", filename)[-3]
    id = int(split)

    print("ID detected from filename as " + str(id))

    sd = NoeBitStream()
    vt = NoeBitStream()
    fc = NoeBitStream()
    mf = NoeBitStream()
    global doNorms, bDoAutoScale, bNoGuns, bNoShotgun, bNoGear
    ctx = rapi.rpgCreateContext()

    bNoGuns = noesis.optWasInvoked("-noguns")
    bNoShotgun = noesis.optWasInvoked("-noshotgun")
    bNoGear = noesis.optWasInvoked("-nogear")


    print ("			----TR7AE Mesh Export 1.97 by Raq----			\n")
    print ("Export Parameters:")
    print (" -noguns  =  Export with the holstered guns removed")
    print (" -noshotgun  =  Export with the holstered shotgun removed")
    print (" -nogear  =  Export with all gear attachments removed\n")

    def getExportName():
		
        newMeshName = ((re.sub(r'\.mesh\..*', "", rapi.getInputName().lower()).replace(".meshout","")).replace(".fbx","").replace(".tr7aemesh","").replace("out.",""))
        newMeshName = noesis.userPrompt(noesis.NOEUSERVAL_FILEPATH, "Export over tr7aemesh", "Choose 5_0.tr7aemesh from lara.drm. You cannot export over any other file.", newMeshName + ".tr7aemesh", None)
        if newMeshName == None:
            print("Aborting...")
            return
        return newMeshName

    def roundByte(value):
        if value < 0: 
            value -= 1 
        else:
            value += 1
        return int(value)

    newMeshName = getExportName()
    if newMeshName == None:
        return 0
    while not (rapi.checkFileExists(newMeshName)):
        print ("File not found!")
        newMeshName = getExportName()	
        if newMeshName == None:
            return 0

    newMesh = rapi.loadIntoByteArray(newMeshName)
    z = NoeBitStream(newMesh)

    if noesis.optWasInvoked("-noguns"):
        print ("Exporting with removed holstered guns attachment")
        bNoGuns = True

    if noesis.optWasInvoked("-noshotgun"):
        print ("Exporting with removed holstered shotgun attachment")
        bNoShotgun = True

    if noesis.optWasInvoked("-nogear"):
        print ("Exporting with removed gear attachments (grapple hook excluded)")
        bNoGear = True

    #Write header
    sd.seek(0)
    sd.writeInt(79823955) #version
    sd.writeInt(len(mdl.bones)) #bone count
    #VirtSegments Count, write later
    virtSegmentsCount = sd.tell()
    sd.writeInt(0)
    #Bone offset, write later
    boneOffset = sd.tell()
    sd.writeInt(0)
    #ModelScale
    ModelScale = sd.tell()
    sd.writeFloat(0.005000000)
    sd.writeFloat(0.005000000)
    sd.writeFloat(0.005000000)
    sd.writeFloat(1)
    #Vertex Count, write later
    vertexCount = sd.tell()
    sd.writeInt(0)
    #Vertex Offset, write later
    vertexOffset = sd.tell()
    sd.writeInt(0)
    sd.writeInt(0)
    sd.writeInt(0)
    #Face count, write later
    faceCount = sd.tell()
    sd.writeInt(0)
    sd.writeInt(0)
    sd.writeInt(0)
    sd.writeFloat(509.1641)
    sd.writeFloat(259248.1)
    sd.writeInt(0)
    sd.writeInt(0)
    sd.writeInt(0)
    sd.writeInt(0)
    sd.writeInt(0)
    #Face offset, write later
    faceOffset = sd.tell()
    sd.writeInt(0)
    #envMappedVertices is something to do with writing an additional vertex list to add some kind of property to them, normally written in another file
    #I don't know exactly what these properties are and it seems like little to none original models of the game are using them, so it just gets nulled by setting its offset to the offset to nextTexture (00 00 00 00)
    envMappedVertices = sd.tell()
    sd.writeInt(0)
    #EyeRefEnvMappedVertices is also...well, just copy what I said above
    EyeRefEnvMappedVertices = sd.tell()
    sd.writeInt(0)
    sd.writeInt(0)
    sd.writeInt(0)
    sd.writeInt(0)
    sd.writeInt(0)
    #boneMirrorDataOffset from here, but it can't be 0. It needs to be the specific data from the specific mesh file you're replacing. I'll look more into this in the future. EDIT: Looks like this data can actually stay the same for every character, if the data is Lara's. Because she is the only one to have gameplay animations therefore the only one to have mirrored animations.
    boneMirrorData = sd.tell()
    sd.writeInt(372)
    drawgroupCenter = sd.tell()
    sd.writeInt(148)
    sd.writeInt(0)
    sd.writeInt(0)
    sd.writeInt(0)
    sd.writeInt(0)
    sd.writeInt(0)
    sd.writeInt(0)
    sd.writeInt(458752)
    sd.writeInt(295)
    #Write a bunch of zeros for whatever reason
    for i in range(52):
        sd.writeInt(0)
    sd.writeInt(-1441792)
    sd.writeInt(470)
    sd.writeInt(201394954)
    sd.writeInt(302842135)
    sd.writeInt(17894913)
    sd.writeInt(318836751)
    sd.writeInt(488178197)
    sd.writeInt(19540226)
    sd.writeInt(973223990)
    sd.writeInt(1768232271)
    sd.writeInt(4)
    sd.writeInt(0)
    sd.writeInt(0)

    #Write skeleton
    startofBones = sd.tell()
    # bones = noeCalculateLocalBoneTransforms(sorted(mdl.bones, key=lambda joint: joint.name))
    finalJointList = sorted(mdl.bones, key=lambda joint: joint.name)
    permIndices = [i[0] for i in sorted(enumerate(mdl.bones), key=lambda j:j[1].name)]
    indexRemap = {}
    for i,f in enumerate(permIndices):
        indexRemap[f] = i
        indexRemap[-1] = -1
    for b, bone in enumerate(finalJointList):
        #Null all the min/max values, they are probably for bounding boxes used during development and they're useless
        sd.writeFloat(0)
        sd.writeFloat(0)
        sd.writeFloat(0)
        sd.writeUInt(0)
        sd.writeFloat(0)
        sd.writeFloat(0)
        sd.writeFloat(0)
        sd.writeUInt(0)
        #Write the transforms
        if indexRemap[bone.parentIndex] >= 0:
            mat = bone.getMatrix() * finalJointList[indexRemap[bone.parentIndex]].getMatrix().inverse()
        else:
            mat = bone.getMatrix()
        mat[3] *= (1 / 1)
        sd.writeFloat(mat[3][0])
        sd.writeFloat(mat[3][1])
        sd.writeFloat(mat[3][2])
        sd.writeUInt(1065353216)
        #Flags
        sd.writeUInt(0)
        #Nulling First/LastVertex for every bone because I'm just writing a VirtSegment for each vertex
        #FirstVertex
        sd.writeShort(0)
        #LastVertex
        sd.writeShort(-1)
        #BoneParent
        sd.writeUInt(indexRemap[bone.parentIndex])
        #HInfo
        sd.writeUInt(0)

    #Write VirtSegments
    finalPositions = []
    startofVirtSegments = sd.tell()
    virtsBefore = 0
    for m, mesh in enumerate(mdl.meshes):
        f = []
        for vertIdx,skinVert in enumerate(mesh.weights):

            #Null all the min/max values, they are probably for bounding boxes used during development and they're useless
            sd.writeFloat(0)
            sd.writeFloat(0)
            sd.writeFloat(0)
            sd.writeUInt(0)
            sd.writeFloat(0)
            sd.writeFloat(0)
            sd.writeFloat(0)
            sd.writeUInt(0)
            #Write the transforms
            if len(skinVert.indices)>1:
                whateverIdx = indexRemap[skinVert.indices[1]]
            if len(skinVert.indices)==1:
                whateverIdx = indexRemap[skinVert.indices[0]]
            if len(skinVert.indices)>1:
                if (skinVert.indices[0])>(skinVert.indices[1]):
                    whateverIdx = indexRemap[skinVert.indices[0]]
                if (skinVert.indices[0])<(skinVert.indices[1]):
                    whateverIdx = indexRemap[skinVert.indices[1]]


            bone = finalJointList[whateverIdx]
            mat2 = bone.getMatrix() * finalJointList [indexRemap[bone.parentIndex]].getMatrix().inverse()
            jointPos = finalJointList[whateverIdx].getMatrix()[3]

            transforms = sd.tell()
            if len(skinVert.weights)>1:
                if (skinVert.indices[0])>(skinVert.indices[1]):
                     sd.writeFloat(mat2[3][0])
                     sd.writeFloat(mat2[3][1])
                     sd.writeFloat(mat2[3][2])
                     sd.writeFloat(1)
                if (skinVert.indices[0])<(skinVert.indices[1]):
                     sd.writeFloat(-mat2[3][0])
                     sd.writeFloat(-mat2[3][1])
                     sd.writeFloat(-mat2[3][2])
                     sd.writeFloat(1)
            if len(skinVert.weights)==1:
                sd.writeFloat(0)
                sd.writeFloat(0)
                sd.writeFloat(0)
                sd.writeFloat(0)
            #Flags
            sd.writeInt(8)
            #FirstVertex
            sd.writeShort(vertIdx + virtsBefore)
            #LastVertex
            sd.writeShort(vertIdx + virtsBefore)
            #write index, weightIndex and weight
            if len(skinVert.indices)>1:
                if (skinVert.indices[0])>(skinVert.indices[1]):
                    #write index
                    sd.writeShort(indexRemap[skinVert.indices[0]])
                    #get index
                    sd.seek(-2, NOESEEK_REL)
                    index = sd.readShort()
                    #write weightIndex
                    sd.writeShort(indexRemap[skinVert.indices[1]])
                    #get weightIndex
                    sd.seek(-2, NOESEEK_REL)
                    weightIndex = sd.readShort()
                    #write weight
                    sd.writeFloat(skinVert.weights[1])
                    #get weight
                    sd.seek(-4, NOESEEK_REL)
                    weight = sd.readFloat()
                    sd.seek(transforms)
                    if index > weightIndex:
                        bone = finalJointList[weightIndex]
                        bone2 = finalJointList[index]
                        mat2 = bone.getMatrix() * finalJointList [indexRemap[bone.parentIndex]].getMatrix().inverse()
                        mat3 = bone2.getMatrix() * finalJointList [indexRemap[bone.parentIndex]].getMatrix().inverse()
                        sd.writeFloat(-mat2[3][0] + mat3[3][0])
                        sd.writeFloat(-mat2[3][1] + mat3[3][1])
                        sd.writeFloat(-mat2[3][2] + mat3[3][2])
                        sd.writeFloat(1)
                        sd.writeInt(8)
                        sd.writeShort(vertIdx + virtsBefore)
                        sd.writeShort(vertIdx + virtsBefore)
                        sd.writeShort(index)
                        sd.writeShort(weightIndex)
                        sd.writeFloat(weight)
                    if weightIndex > index:
                        bone = finalJointList[weightIndex]
                        bone2 = finalJointList[index]
                        mat2 = bone.getMatrix() * finalJointList [indexRemap[bone.parentIndex]].getMatrix().inverse()
                        mat3 = bone2.getMatrix() * finalJointList [indexRemap[bone.parentIndex]].getMatrix().inverse()
                        sd.writeFloat(-mat2[3][0] + mat3[3][0])
                        sd.writeFloat(-mat2[3][1] + mat3[3][1])
                        sd.writeFloat(-mat2[3][2] + mat3[3][2])
                        sd.writeFloat(1)
                        sd.writeInt(8)
                        sd.writeShort(vertIdx + virtsBefore)
                        sd.writeShort(vertIdx + virtsBefore)
                        sd.writeShort(index)
                        sd.writeShort(weightIndex)
                        sd.writeFloat(weight)

                if (skinVert.indices[0])<(skinVert.indices[1]):
                    #write index
                    sd.writeShort(indexRemap[skinVert.indices[1]])
                    #get index
                    sd.seek(-2, NOESEEK_REL)
                    index = sd.readShort()
                    #write weightIndex
                    sd.writeShort(indexRemap[skinVert.indices[0]])
                    #get weightIndex
                    sd.seek(-2, NOESEEK_REL)
                    weightIndex = sd.readShort()
                    #write weight
                    sd.writeFloat(skinVert.weights[0])
                    #get weight
                    sd.seek(-4, NOESEEK_REL)
                    weight = sd.readFloat()
                    sd.seek(transforms)
                    if index > weightIndex:
                        bone = finalJointList[weightIndex]
                        bone2 = finalJointList[index]
                        mat2 = bone.getMatrix() * finalJointList [indexRemap[bone.parentIndex]].getMatrix().inverse()
                        mat3 = bone2.getMatrix() * finalJointList [indexRemap[bone.parentIndex]].getMatrix().inverse()
                        sd.writeFloat(-mat2[3][0] + mat3[3][0])
                        sd.writeFloat(-mat2[3][1] + mat3[3][1])
                        sd.writeFloat(-mat2[3][2] + mat3[3][2])
                    if weightIndex > index:
                        bone = finalJointList[weightIndex]
                        bone2 = finalJointList[index]
                        mat2 = bone.getMatrix() * finalJointList [indexRemap[bone.parentIndex]].getMatrix().inverse()
                        mat3 = bone2.getMatrix() * finalJointList [indexRemap[bone.parentIndex]].getMatrix().inverse()
                        sd.writeFloat(-mat2[3][0] + mat3[3][0])
                        sd.writeFloat(-mat2[3][1] + mat3[3][1])
                        sd.writeFloat(-mat2[3][2] + mat3[3][2])

            else:
                sd.writeShort(indexRemap[skinVert.indices[0]])
                sd.seek(-2, NOESEEK_REL)
                index = sd.readShort()
                sd.writeShort(indexRemap[skinVert.indices[0]])
                sd.seek(-2, NOESEEK_REL)
                weightIndex = sd.readShort()
                sd.writeFloat(skinVert.weights[0])
                sd.seek(-4, NOESEEK_REL)
                weight = sd.readFloat()

            finalPos = finalJointList[indexRemap[skinVert.indices[0]]].getMatrix().inverse().transformPoint(mesh.positions[vertIdx])
            f.append(finalPos)
        finalPositions.append(f)
        virtsBefore += len(mesh.positions)

    #Write HInfo - THIS IS EXPERIMENTAL AND VERY BROKEN - DELETE THIS BUNCH OF BULLSHIT SOONER OR LATER

	#Clone HInfo

    z.seek(15168, NOESEEK_ABS) 
    sd.writeBytes(z.readBytes(1176))

    #Get all the offsets of the start of each list

    startofHInfo = sd.tell()

    sd.seek(-1144, NOESEEK_REL)
    startofSphere0 = sd.tell()
    sd.seek(56, NOESEEK_REL)
    startofSphere1 = sd.tell()
    sd.seek(24, NOESEEK_REL)
    startofMarker1 = sd.tell()
    sd.seek(352, NOESEEK_REL)
    startofMarker2 = sd.tell()
    sd.seek(160, NOESEEK_REL)
    startofMarker3 = sd.tell()
    sd.seek(64, NOESEEK_REL)
    startofMarker4 = sd.tell()
    sd.seek(64, NOESEEK_REL)
    startofSphere2 = sd.tell()
    sd.seek(64, NOESEEK_REL)
    startofMarker5 = sd.tell()
    sd.seek(64, NOESEEK_REL)
    startofSphere3 = sd.tell()
    sd.seek(24, NOESEEK_REL)
    startofMarker6 = sd.tell()
    sd.seek(128, NOESEEK_REL)
    startofMarker7 = sd.tell()
    sd.seek(64, NOESEEK_REL)
    startofSphere4 = sd.tell()
    sd.seek(56, NOESEEK_REL)
    startofMarker8 = sd.tell()
    sd.seek(24, NOESEEK_REL)
    readsomething = sd.readUInt()

    #Get all the offsets of the start of each HInfo

    sd.seek(-1176, NOESEEK_REL)
    startHInfo0 = sd.tell()
    sd.seek(56, NOESEEK_REL)
    startHInfo1 = sd.tell()
    sd.seek(376, NOESEEK_REL)
    startHInfo2 = sd.tell()
    sd.seek(160, NOESEEK_REL)
    startHInfo3 = sd.tell()
    sd.seek(64, NOESEEK_REL)
    startHInfo4 = sd.tell()
    sd.seek(64, NOESEEK_REL)
    startHInfo5 = sd.tell()
    sd.seek(56, NOESEEK_REL)
    startHInfo6 = sd.tell()
    sd.seek(64, NOESEEK_REL)
    startHInfo7 = sd.tell()
    sd.seek(152, NOESEEK_REL)
    startHInfo8 = sd.tell()
    sd.seek(64, NOESEEK_REL)
    startHInfo9 = sd.tell()
    sd.seek(56, NOESEEK_REL)
    startHInfo10 = sd.tell()
    sd.seek(56, NOESEEK_REL)
    endofHInfo = sd.tell()

    #Fix HInfo lists

    sd.seek(-1164, NOESEEK_REL)
    sd.writeInt(startofSphere0)
    sd.seek(52, NOESEEK_REL)
    sd.writeInt(startofSphere1)
    sd.seek(12, NOESEEK_REL)
    sd.writeInt(startofMarker1)
    sd.seek(372, NOESEEK_REL)
    sd.writeInt(startofMarker2)
    sd.seek(156, NOESEEK_REL)
    sd.writeInt(startofMarker3)
    sd.seek(60, NOESEEK_REL)
    sd.writeInt(startofMarker4)
    sd.seek(44, NOESEEK_REL)
    sd.writeInt(startofSphere2)
    sd.seek(68, NOESEEK_REL)
    sd.writeInt(startofMarker5 - 8)
    sd.seek(44, NOESEEK_REL)
    sd.writeInt(startofSphere3 - 8)
    sd.seek(12, NOESEEK_REL)
    sd.writeInt(startofMarker6 - 8)
    sd.seek(148, NOESEEK_REL)
    sd.writeInt(startofMarker7 - 8)
    sd.seek(44, NOESEEK_REL)
    sd.writeInt(startofSphere4 - 8)
    sd.seek(68, NOESEEK_REL)
    sd.writeInt(startofMarker8 - 8)

    #Write HInfo offsets in the bones

    sd.seek(540)
    sd.writeUInt(startHInfo0)
    sd.seek(668)
    sd.writeUInt(startHInfo1)
    sd.seek(796)
    sd.writeUInt(startHInfo2)
    sd.seek(4188)
    sd.writeUInt(startHInfo3)
    sd.seek(5340)
    sd.writeUInt(startHInfo4)
    sd.seek(5724)
    sd.writeUInt(startHInfo5)
    sd.seek(6684)
    sd.writeUInt(startHInfo6)
    sd.seek(6876)
    sd.writeUInt(startHInfo7)
    sd.seek(6940)
    sd.writeUInt(startHInfo8)
    sd.seek(7068)
    sd.writeUInt(startHInfo9)
    sd.seek(7196)
    sd.writeUInt(startHInfo10)
    sd.seek(endofHInfo)

    #get lists offsets for relocations

    sd.seek(-1172, NOESEEK_REL)
    offset1 = sd.tell()
    sd.seek(40, NOESEEK_REL)
    offset2 = sd.tell()
    sd.seek(16, NOESEEK_REL)
    offset3 = sd.tell()
    sd.seek(376, NOESEEK_REL)
    offset4 = sd.tell()
    sd.seek(160, NOESEEK_REL)
    offset5 = sd.tell()
    sd.seek(64, NOESEEK_REL)
    offset6 = sd.tell()
    sd.seek(48, NOESEEK_REL)
    offset7 = sd.tell()
    sd.seek(72, NOESEEK_REL)
    offset8 = sd.tell()
    sd.seek(48, NOESEEK_REL)
    offset9 = sd.tell()
    sd.seek(16, NOESEEK_REL)
    offset10 = sd.tell()
    sd.seek(152, NOESEEK_REL)
    offset11 = sd.tell()
    sd.seek(48, NOESEEK_REL)
    offset12 = sd.tell()
    sd.seek(72, NOESEEK_REL)
    offset13 = sd.tell()
    sd.seek(40, NOESEEK_REL)
    offset13 = sd.tell()
    sd.seek(endofHInfo)
    z.seek(16336, NOESEEK_ABS)
    sd.writeBytes(z.readBytes(8))

    if bNoGuns:
        bNoGuns = True
        sd.seek(endofHInfo)
        sd.seek(-8, NOESEEK_REL)
        sd.writeInt(-1)
        sd.seek(-124, NOESEEK_REL)
        sd.writeInt(-1)
        sd.seek(132, NOESEEK_REL)

    if bNoShotgun:
        bNoShotgun = True
        sd.seek(endofHInfo)
        sd.seek(-784, NOESEEK_REL)
        sd.writeInt(-1)
        sd.seek(788, NOESEEK_REL)

    if bNoGear:
        bNoGear = True
        sd.seek(endofHInfo)

        #HInfo1
        sd.seek(-1040, NOESEEK_REL)
        sd.writeInt(-1)
        sd.seek(28, NOESEEK_REL)
        sd.writeInt(-1)
        sd.seek(28, NOESEEK_REL)
        sd.writeInt(-1)
        sd.seek(28, NOESEEK_REL)
        sd.writeInt(-1)
        sd.seek(28, NOESEEK_REL)
        sd.writeInt(-1)
        sd.seek(28, NOESEEK_REL)
        sd.writeInt(-1)
        sd.seek(28, NOESEEK_REL)
        sd.writeInt(-1)
        sd.seek(28, NOESEEK_REL)
        sd.writeInt(-1)
        sd.seek(28, NOESEEK_REL)
        sd.writeInt(-1)
        sd.seek(28, NOESEEK_REL)
        sd.writeInt(-1)

        #HInfo2
        sd.seek(60, NOESEEK_REL)
        sd.writeInt(-1)
        sd.seek(28, NOESEEK_REL)
        sd.writeInt(-1)
        sd.seek(28, NOESEEK_REL)
        sd.writeInt(-1)
        sd.seek(28, NOESEEK_REL)
        sd.writeInt(-1)

        #HInfo3
        sd.seek(60, NOESEEK_REL)
        sd.writeInt(-1)

        #HInfo7
        sd.seek(332, NOESEEK_REL)
        sd.writeInt(-1)

        #HInfo8
        sd.seek(60, NOESEEK_REL)
        sd.writeInt(-1)

        #HInfo10
        sd.seek(116, NOESEEK_REL)
        sd.writeInt(-1)
        sd.seek(12, NOESEEK_REL)


    #Write vertices
    startofVertexBuffer = sd.tell()
    numVerts = 0
    vortsBefore = 0
    for m, mesh in enumerate(mdl.meshes):
        numVerts += len(finalPositions[m])
    
        for v, vertexPos in enumerate(finalPositions[m]):
    
            #Positions
            vt.writeUShort(int(vertexPos[0] / 0.005000000))
            vt.writeUShort(int(vertexPos[1] / 0.005000000))
            vt.writeUShort(int(vertexPos[2] / 0.005000000))
    
            #Normals
            vt.writeByte(int(mesh.normals[v][0] * 127 + 0.5000000001))
            vt.writeByte(int(mesh.normals[v][1] * 127 + 0.5000000001))
            vt.writeByte(int(mesh.normals[v][2] * 127 + 0.5000000001))
    
            #Pad
            vt.writeByte(0)
            
            #BoneID
            vt.writeShort(v + len(mdl.bones) + vortsBefore)
            
            #UV
            u = int.from_bytes(struct.pack("f", mesh.uvs[v][0]), "little")
            v = int.from_bytes(struct.pack("f", mesh.uvs[v][1]), "little")
            if u & 0xFFFF >= 0x8000: u += 1 << 16
            if v & 0xFFFF >= 0x8000: v += 1 << 16
            vt.writeUInt(v & 0xFFFF << 16 | u >> 16)
    
        vortsBefore += len(mesh.positions)

    #Write TextureStripInfo (polygons)
    startofFaces = sd.tell()
    vertsBefore = 0
    offsetlist = []

    for m, mesh in enumerate(mdl.meshes):

        print ("Writing " + str(mesh.name))

        if mesh.name.find('.') != -1:
            print ("Renaming Mesh " + str(mesh.name) + " to " + str(mesh.name.split('.')[0]))
            mesh.name = mesh.name.split('.')[0]

        #Face section header
        startofFaceSection = fc.tell()
        if len(mesh.indices) > 32767:
            print ("\nERROR: One of the meshes exceeds the limit of 10922 faces")
            return 0
        fc.writeShort(len(mesh.indices))
        drawgroup = fc.tell()
        #Get mesh names strings to write tpageid and drawgroup
        splitted = mesh.name.split("_")

        if len(splitted) == 11: #Check this shit because I'm not even sure it works, it's supposed to always remove those weird numbers at the start of the mesh names
            del splitted[0]

        if len(splitted) != 10:
            print ("\nERROR: The name of one or more of your meshes is written incorrectly")
            return 0
        fc.writeShort(int(splitted[9])) #drawgroup
        texture = (int(splitted[3]))
        blend = (int(splitted[5])) << 13
        unkn1 = 0 << 17
        singlesided = (int(splitted[7])) << 21
        unkn2 = 0 << 22
        tpageid = texture | blend | unkn1 | singlesided | unkn2
        fc.writeInt(tpageid)
        fc.writeFloat(0) #sortPush
        fc.writeFloat(0) #scrollOffset
        fc.writeUInt(0) #nextTexture

        #Write mesh indices
        for idx in mesh.indices:
            fc.writeUShort(idx + vertsBefore)
        while ((fc.tell() & 3) != 0):
            fc.writeByte(0xff) #padding
        vertsBefore += len(mesh.positions)
        nextTexture = fc.tell()
            #Get offset of the next face section then go back to nextTexture to write it
        fc.seek(startofFaceSection + 16)
        nextTextureOffset = fc.tell()
        offsetlist.append(nextTextureOffset + len(vt.getBuffer()) + len(sd.getBuffer()))
        fc.writeUInt(nextTexture + len(sd.getBuffer()) + len(vt.getBuffer()))
        fc.seek(nextTexture)
    zeros = fc.tell() + (len(vt.getBuffer())) + (len(sd.getBuffer()))
    fc.writeUInt(0)
    size = (len(sd.getBuffer())) + (len(vt.getBuffer())) + (len(fc.getBuffer()))

    #Adjust header
    sd.seek(boneOffset)
    sd.writeInt(startofBones)
    sd.seek(virtSegmentsCount)
    sd.writeInt(numVerts)
    sd.seek(vertexCount)
    sd.writeInt(numVerts)
    sd.seek(vertexOffset)
    sd.writeInt(startofVertexBuffer)
    sd.seek(faceCount)
    sd.writeInt(0)
    sd.seek(faceOffset)
    #Face offset, write later
    sd.writeInt(0)
    sd.seek(envMappedVertices)
    sd.writeInt(zeros)
    sd.seek(EyeRefEnvMappedVertices)
    sd.writeInt(zeros)

    #Write Vertex Buffer
    sd.seek(startofVertexBuffer)
    sd.writeBytes(vt.getBuffer())
    startofFaces = sd.tell()
    sd.seek(faceOffset)
    sd.writeInt(startofFaces)

    #Write Face Data
    sd.seek(startofFaces)
    sd.writeBytes(fc.getBuffer())

    #Write MFace Data
    sd.seek(startofFaces)
    sd.writeBytes(mf.getBuffer())

    #Write Section Data
    bs.writeString("SECT", False)	# cdcEngineTools section magic
    bs.writeInt(size)
    bs.writeInt(0)
    bs.writeInt(31 + len(mdl.meshes) << 8) # numRelocations
    bs.writeInt(0)
    bs.writeUInt(4294967295)
    #Write relocations
    bs.writeInt(id << 3)
    bs.writeUInt(boneOffset)
    bs.writeInt(id << 3)
    bs.writeUInt(vertexOffset)
    bs.writeInt(id << 3)
    bs.writeUInt(faceOffset)
    bs.writeInt(id << 3)
    bs.writeUInt(envMappedVertices)
    bs.writeInt(id << 3)
    bs.writeUInt(EyeRefEnvMappedVertices)
    bs.writeInt(id << 3)
    bs.writeUInt(boneMirrorData)
    bs.writeInt(id << 3)
    bs.writeUInt(drawgroupCenter)
    z.seek(120, NOESEEK_ABS) 
    bs.writeBytes(z.readBytes(88))
    bs.writeInt(id << 3)
    bs.writeUInt(offset1 + 8)
    bs.writeInt(id << 3)
    bs.writeUInt(offset2 + 24)
    bs.writeInt(id << 3)
    bs.writeUInt(offset3 + 24)
    bs.writeInt(id << 3)
    bs.writeUInt(offset4 + 24)
    bs.writeInt(id << 3)
    bs.writeUInt(offset5 + 28 - 4)
    bs.writeInt(id << 3)
    bs.writeUInt(offset6 + 40 - 16)
    bs.writeInt(id << 3)
    bs.writeUInt(offset7 + 24)
    bs.writeInt(id << 3)
    bs.writeUInt(offset8 + 48 - 24)
    bs.writeInt(id << 3)
    bs.writeUInt(offset9 + 24)
    bs.writeInt(id << 3)
    bs.writeUInt(offset10 - 8 + 32)
    bs.writeInt(id << 3)
    bs.writeUInt(offset11 - 24 + 48)
    bs.writeInt(id << 3)
    bs.writeUInt(offset12 - 24 + 48)
    bs.writeInt(id << 3)
    bs.writeUInt(offset13 - 16)

    for m, mesh in enumerate(mdl.meshes):

        bs.writeInt(id << 3)
        bs.writeUInt(offsetlist[m])

    bs.writeBytes(sd.getBuffer())

    #Fix section reference of written HInfo relocations

    bs.seek(80)
    bs.writeInt(id << 3)
    bs.seek(4, NOESEEK_REL)
    bs.writeInt(id << 3)
    bs.seek(4, NOESEEK_REL)
    bs.writeInt(id << 3)
    bs.seek(4, NOESEEK_REL)
    bs.writeInt(id << 3)
    bs.seek(4, NOESEEK_REL)
    bs.writeInt(id << 3)
    bs.seek(4, NOESEEK_REL)
    bs.writeInt(id << 3)
    bs.seek(4, NOESEEK_REL)
    bs.writeInt(id << 3)
    bs.seek(4, NOESEEK_REL)
    bs.writeInt(id << 3)
    bs.seek(4, NOESEEK_REL)
    bs.writeInt(id << 3)
    bs.seek(4, NOESEEK_REL)
    bs.writeInt(id << 3)
    bs.seek(4, NOESEEK_REL)
    bs.writeInt(id << 3)

    return 1

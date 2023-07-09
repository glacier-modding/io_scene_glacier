<a href="https://wiki.glaciermodding.org/blender">
	<img src="https://img.shields.io/badge/docusaurus-wiki.glaciermodding.org-brightgreen" />
</a>

# Glacier 2 Blender addon
*View and create assets from the Glacier 2 game engine.*  

![lod_slider](https://user-images.githubusercontent.com/43296291/203970131-4080b2cb-c09e-49e4-b8a9-5aa9a9a61d50.gif)

## Supported Titles and Features
The following games are supported by this addon:

 * Hitman 2016
 * Hitman 2
 * Hitman 3

The addon supports the following formats:

| Extension     | Description                    | Can import | Can export |
| ------------- | ------------------------------ | :--------: | :--------: |
| .prim         | Standard RenderPrimitive       |    Yes     |    Yes     |
| .weightedprim | Weighted RenderPrimitive       |    Yes     |     No     |
| .linkedprim   | Linked RenderPrimitive         |    Yes     |     No     |
| .borg         | AnimationBoneData              |    Yes     |     No     |
| .aloc         | Physics                        |     No     |     Yes    |
| .mjba         | MorphemeJointBoneAnimationData |     No     |     No     |
| .mrtr         | MorphemeRuntimeRig             |     No     |     No     |
| .vtxd         | VertexData                     |     No     |     No     |
 
*Support for more formats or titles may be added in the future*
 
## Requirements
 - Blender **3.0.0** or above

## Installation
 - Download the addon: **[Glacier 2  addon](https://github.com/glacier-modding/io_scene_glacier/archive/master.zip)**
 - Install the addon in blender like so:
   - go to *Edit > Preferences > Add-ons.*
   - use the *Install…* button and use the File Browser to select the `.zip`

## Credits

 * [PawREP](https://github.com/pawREP)
   * For making the original `.prim` editing tool known as PrimIO that was used as a reference.


 * [Khronos Group](https://github.com/KhronosGroup)
   * For making glTF-Blender-IO that was used as a reference addon.
   

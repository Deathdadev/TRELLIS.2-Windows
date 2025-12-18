"""
Script to automatically fix FlexGEMM, CuMesh, and o-voxel files for Windows compatibility.
This script replaces undefined 'uint' types with 'uint32_t' in the neighbor_map.cu file, adds necessary compilation flags to CuMesh setup.py, and fixes MSVC compatibility issues in o-voxel source files.
"""

import os
import platform

def fix_flexgemm_cuda_file():
    """Fix the FlexGEMM CUDA file by replacing 'uint' with 'uint32_t'."""
    file_path = 'tmp/extensions/FlexGEMM/flex_gemm/kernels/cuda/spconv/neighbor_map.cu'
    
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if fixes are needed
    original_content = content
    content = content.replace('uint tmp = neigh_map[n * V + v];', 'uint32_t tmp = neigh_map[n * V + v];')
    content = content.replace('*(uint*)&neigh_map_T[v * N + n + n_base] = tmp;', '*(uint32_t*)&neigh_map_T[v * N + n + n_base] = tmp;')
    content = content.replace('*(uint*)&neigh_mask_T[v * N + n + n_base] = tmp;', '*(uint32_t*)&neigh_mask_T[v * N + n + n_base] = tmp;')
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Fixed FlexGEMM CUDA file for Windows compatibility.")
    else:
        print("FlexGEMM CUDA file already fixed or no changes needed.")

def fix_cumesh_setup():
    """Fix the CuMesh setup.py by adding necessary compilation flags."""
    file_path = 'tmp/extensions/CuMesh/setup.py'
    
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # For cumesh._C nvcc: add -Xcudafe --diag_suppress=2872
    if '"-Xcudafe"' not in content or '"--diag_suppress=2872"' not in content:
        old = '"nvcc": ["-O3","-std=c++17"] + cc_flag,'
        new = '"nvcc": ["-O3","-std=c++17"] + cc_flag + [\n                    "-Xcudafe", "--diag_suppress=2872",\n                ],'
        content = content.replace(old, new)
    
    # For cumesh._cubvh cxx: add -Dssize_t=ptrdiff_t
    cubvh_start = content.find("name='cumesh._cubvh'")
    xatlas_start = content.find("name='cumesh._xatlas'")
    if cubvh_start != -1 and xatlas_start != -1:
        cubvh_section = content[cubvh_start:xatlas_start]
        if '"-Dssize_t=ptrdiff_t"' not in cubvh_section:
            old = '"cxx": ["-O3", "-std=c++17"],'
            new = '"cxx": ["-O3", "-std=c++17", "-Dssize_t=ptrdiff_t"],'
            # Replace only in cubvh_section
            cubvh_section_new = cubvh_section.replace(old, new, 1)
            content = content.replace(cubvh_section, cubvh_section_new)
    
    # For cumesh._cubvh nvcc: add -Xcudafe --diag_suppress=2872
    cubvh_nvcc_old = '''"nvcc": ["-O3","-std=c++17"] + cc_flag + [
                    "--extended-lambda",
                    "--expt-relaxed-constexpr",
                    # The following definitions must be undefined
                    # since we need half-precision operation.
                    "-U__CUDA_NO_HALF_OPERATORS__",
                    "-U__CUDA_NO_HALF_CONVERSIONS__",
                    "-U__CUDA_NO_HALF2_OPERATORS__",
                ]'''
    cubvh_nvcc_new = '''"nvcc": ["-O3","-std=c++17"] + cc_flag + [
                    "--extended-lambda",
                    "--expt-relaxed-constexpr",
                    # The following definitions must be undefined
                    # since we need half-precision operation.
                    "-U__CUDA_NO_HALF_OPERATORS__",
                    "-U__CUDA_NO_HALF_CONVERSIONS__",
                    "-U__CUDA_NO_HALF2_OPERATORS__",
                    "-Xcudafe", "--diag_suppress=2872",
                ]'''
    if cubvh_nvcc_old in content:
        content = content.replace(cubvh_nvcc_old, cubvh_nvcc_new)
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Fixed CuMesh setup.py for Windows compatibility.")
    else:
        print("CuMesh setup.py already fixed or no changes needed.")

def fix_o_voxel_files():
    """Fix the o-voxel source files for MSVC compatibility."""
    base_path = 'tmp/extensions/o-voxel'
    
    # Fix src/io/svo.cpp
    file_path = os.path.join(base_path, 'src/io/svo.cpp')
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        # Fix narrowing conversions
        content = content.replace(
            'torch::Tensor codes_tensor = torch::from_blob(codes.data(), {codes.size()}, torch::kInt32).clone();',
            'torch::Tensor codes_tensor = torch::from_blob(codes.data(), {static_cast<int64_t>(codes.size())}, torch::kInt32).clone();'
        )
        content = content.replace(
            'torch::Tensor svo_tensor = torch::from_blob(svo.data(), {svo.size()}, torch::kUInt8).clone();',
            'torch::Tensor svo_tensor = torch::from_blob(svo.data(), {static_cast<int64_t>(svo.size())}, torch::kUInt8).clone();'
        )
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print("Fixed o-voxel src/io/svo.cpp for MSVC compatibility.")
        else:
            print("o-voxel src/io/svo.cpp already fixed or no changes needed.")
    
    # Fix src/io/filter_neighbor.cpp
    file_path = os.path.join(base_path, 'src/io/filter_neighbor.cpp')
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        # Fix narrowing conversions in tensor creations
        content = content.replace(
            '    // Pack the deltas into a uint8 tensor\n    torch::Tensor delta = torch::zeros({N, C}, torch::dtype(torch::kUInt8));',
            '    // Pack the deltas into a uint8 tensor\n    torch::Tensor delta = torch::zeros({static_cast<int64_t>(N), static_cast<int64_t>(C)}, torch::dtype(torch::kUInt8));'
        )
        content = content.replace(
            '    // Pack the attribute into a uint8 tensor\n    torch::Tensor attr = torch::zeros({N, C}, torch::dtype(torch::kUInt8));',
            '    // Pack the attribute into a uint8 tensor\n    torch::Tensor attr = torch::zeros({static_cast<int64_t>(N), static_cast<int64_t>(C)}, torch::dtype(torch::kUInt8));'
        )
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print("Fixed o-voxel src/io/filter_neighbor.cpp for MSVC compatibility.")
        else:
            print("o-voxel src/io/filter_neighbor.cpp already fixed or no changes needed.")
    
    # Fix src/io/filter_parent.cpp
    file_path = os.path.join(base_path, 'src/io/filter_parent.cpp')
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        # Fix narrowing conversions in tensor creations
        content = content.replace(
            '    torch::Tensor delta = torch::zeros({N_leaf, C}, torch::kUInt8);',
            '    torch::Tensor delta = torch::zeros({static_cast<int64_t>(N_leaf), static_cast<int64_t>(C)}, torch::kUInt8);'
        )
        content = content.replace(
            '    torch::Tensor attr = torch::zeros({N_leaf, C}, torch::kUInt8);',
            '    torch::Tensor attr = torch::zeros({static_cast<int64_t>(N_leaf), static_cast<int64_t>(C)}, torch::kUInt8);'
        )
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print("Fixed o-voxel src/io/filter_parent.cpp for MSVC compatibility.")
        else:
            print("o-voxel src/io/filter_parent.cpp already fixed or no changes needed.")
    
    # Fix src/convert/flexible_dual_grid.cpp
    file_path = os.path.join(base_path, 'src/convert/flexible_dual_grid.cpp')
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        # Fix invalid literal suffixes
        content = content.replace('1e-6d', '1e-6')
        content = content.replace('0.0d', '0.0')
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print("Fixed o-voxel src/convert/flexible_dual_grid.cpp for MSVC compatibility.")
        else:
            print("o-voxel src/convert/flexible_dual_grid.cpp already fixed or no changes needed.")

if __name__ == '__main__':
    if platform.system() == 'Windows':
        fix_flexgemm_cuda_file()
        fix_cumesh_setup()
        fix_o_voxel_files()
    else:
        print("Not on Windows, skipping fixes.")
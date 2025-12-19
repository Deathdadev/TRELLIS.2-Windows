"""
Script to automatically fix FlexGEMM, CuMesh, and o-voxel files for Windows compatibility.
This script replaces undefined 'uint' types with 'uint32_t' in the neighbor_map.cu file, adds necessary compilation flags to CuMesh setup.py, and fixes MSVC compatibility issues in o-voxel source files.
"""

import os
import platform
import re

def fix_flexgemm_cuda_file():
    """Fix the FlexGEMM CUDA file by replacing 'uint' with 'uint32_t'."""
    file_path = 'tmp/extensions/FlexGEMM/flex_gemm/kernels/cuda/spconv/neighbor_map.cu'
    
    try:
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
    except (OSError, UnicodeDecodeError) as e:
        print(f"Error processing {file_path}: {e}")
        return

def fix_cumesh_setup():
    """Fix the CuMesh setup.py by adding necessary compilation flags."""
    file_path = 'tmp/extensions/CuMesh/setup.py'
    
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except (OSError, UnicodeDecodeError) as e:
        print(f"Error reading {file_path}: {e}")
        return
    
    original_content = content
    
    # For cumesh._C nvcc: add -Xcudafe --diag_suppress=2872
    nvcc_section = content.split('"nvcc": [')[1].split('],')[0]
    if '"-Xcudafe"' not in nvcc_section or '"--diag_suppress=2872"' not in nvcc_section:
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
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print("Fixed CuMesh setup.py for Windows compatibility.")
        except (OSError, UnicodeEncodeError) as e:
            print(f"Error writing {file_path}: {e}")
            return
    else:
        print("CuMesh setup.py already fixed or no changes needed.")

def _apply_file_fixes(file_path, replacements, description):
    """Helper function to apply replacements to a file."""
    try:
        if not os.path.exists(file_path):
            return
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        for pattern, replacement in replacements:
            content = re.sub(pattern, replacement, content)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed {description} for MSVC compatibility.")
        else:
            print(f"{description} already fixed or no changes needed.")
    except (OSError, UnicodeError) as e:
        print(f"Error processing {file_path}: {e}")
        return

def fix_o_voxel_files():
    """Fix the o-voxel source files for MSVC compatibility."""
    base_path = 'tmp/extensions/o-voxel'
    
    # Fix src/io/svo.cpp
    svo_fixes = [
        ('torch::Tensor codes_tensor = torch::from_blob(codes.data(), {codes.size()}, torch::kInt32).clone();',
         'torch::Tensor codes_tensor = torch::from_blob(codes.data(), {static_cast<int64_t>(codes.size())}, torch::kInt32).clone();'),
        ('torch::Tensor svo_tensor = torch::from_blob(svo.data(), {svo.size()}, torch::kUInt8).clone();',
         'torch::Tensor svo_tensor = torch::from_blob(svo.data(), {static_cast<int64_t>(svo.size())}, torch::kUInt8).clone();'),
    ]
    _apply_file_fixes(os.path.join(base_path, 'src/io/svo.cpp'), svo_fixes, 'o-voxel src/io/svo.cpp')
    
    # Fix src/io/filter_neighbor.cpp
    neighbor_fixes = [
        (r'(\s*)torch::Tensor\s+(\w+)\s*=\s*torch::zeros\(\{(\w+),\s*(\w+)\},\s*torch::dtype\(torch::kUInt8\)\);',
         r'\1torch::Tensor \2 = torch::zeros({static_cast<int64_t>(\3), static_cast<int64_t>(\4)}, torch::dtype(torch::kUInt8));'),
    ]
    _apply_file_fixes(os.path.join(base_path, 'src/io/filter_neighbor.cpp'), neighbor_fixes, 'o-voxel src/io/filter_neighbor.cpp')
    
    # Fix src/io/filter_parent.cpp
    parent_fixes = [
        (r'(\s*)torch::Tensor\s+(\w+)\s*=\s*torch::zeros\(\{(\w+),\s*(\w+)\},\s*torch::dtype\(torch::kUInt8\)\);',
         r'\1torch::Tensor \2 = torch::zeros({static_cast<int64_t>(\3), static_cast<int64_t>(\4)}, torch::dtype(torch::kUInt8));'),
    ]
    _apply_file_fixes(os.path.join(base_path, 'src/io/filter_parent.cpp'), parent_fixes, 'o-voxel src/io/filter_parent.cpp')
    
    # Fix src/convert/flexible_dual_grid.cpp
    grid_fixes = [
        ('1e-6d', '1e-6'),
        ('0.0d', '0.0'),
    ]
    _apply_file_fixes(os.path.join(base_path, 'src/convert/flexible_dual_grid.cpp'), grid_fixes, 'o-voxel src/convert/flexible_dual_grid.cpp')

def fix_nvdiffrec_manifest():
    """Create MANIFEST.in for nvdiffrec to include header files."""
    manifest_dir = 'tmp/extensions/nvdiffrec'
    manifest_file = os.path.join(manifest_dir, 'MANIFEST.in')
    target_dir = os.path.join(manifest_dir, 'nvdiffrec_render', 'renderutils', 'c_src')
    
    if not os.path.exists(target_dir):
        print(f"Warning: Target directory {target_dir} does not exist. Skipping MANIFEST.in creation.")
        return
    
    expected_content = 'recursive-include nvdiffrec_render/renderutils/c_src *.h\n'
    
    # Check if file exists and has correct content
    if os.path.exists(manifest_file):
        try:
            with open(manifest_file, 'r', encoding='utf-8') as f:
                current_content = f.read()
            if current_content == expected_content:
                print("nvdiffrec MANIFEST.in already has correct content.")
                return
        except (OSError, UnicodeDecodeError) as e:
            print(f"Error reading existing {manifest_file}: {e}")
            # Continue to overwrite
    
    # Create directory if needed and write file
    try:
        os.makedirs(manifest_dir, exist_ok=True)
        with open(manifest_file, 'w', encoding='utf-8') as f:
            f.write(expected_content)
        print("Created/updated nvdiffrec MANIFEST.in for Windows compatibility.")
    except (OSError, UnicodeEncodeError) as e:
        print(f"Error creating/updating {manifest_file}: {e}")

if __name__ == '__main__':
    if platform.system() == 'Windows':
        fix_flexgemm_cuda_file()
        fix_cumesh_setup()
        fix_o_voxel_files()
        fix_nvdiffrec_manifest()
    else:
        print("Not on Windows, skipping fixes.")
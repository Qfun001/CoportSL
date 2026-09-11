#pragma once
// read.h
#ifndef READ_H
#define READ_H

#include <array>
#include <cstddef>

#include "src/physics/fluid/State.h"
#define NSPIN 3

#define DEBUG (0)
#define SFC 0

#define KRHO 0
#define UU 1
#define U1 2
#define U2 3
#define U3 4
#define B1 5
#define B2 6
#define B3 7

#define NPRIM 8

// MACROS
#define NDIM 4
#define DIM 4
#define LOOP_i for (int i = 0; i < DIM; i++)
#define LOOP_ij for (int i = 0; i < DIM; i++) for (int j = 0; j < DIM; j++)
#define LOOP_kl for (int k = 0; k < DIM; k++) for (int l = 0; l < DIM; l++)
#define LOOP_ijk for (int i = 0; i < DIM; i++) for (int j = 0; j < DIM; j++) for (int k = 0; k < DIM; k++)
#define LOOP_ijkl for (int i = 0; i < DIM; i++) for (int j = 0; j < DIM; j++) for (int k = 0; k < DIM; k++) for (int l = 0; l < DIM; l++)

#define D 0
#define S1 1
#define S2 2
#define S3 3
#define TAU 4
#define DS 8

#define PLUS 1
#define MINUS -1
#define BPOL (PLUS)


struct block {
    int ind[3], level, size[3];
    double lb[3], dxc_block[3];
};

struct BhacStencil {
    int igrid;
    int cell;
    double del[3];
    double dx_local[3];
};

struct FloatCopyError {
    double max_absolute = 0.0;
    double max_relative = 0.0;
};

struct GrmhdGridStats {
    size_t leaf_blocks = 0;
    std::array<size_t, 3> cells_per_block_axis = {};
    size_t cells_per_block = 0;
    size_t active_cells = 0;
    size_t primitive_values = 0;
};


extern struct block* block_info;


extern double** Xcoord, *** Xgrid, *** Xbar;
extern std::array<double, 4> stopx, startx, dx;

void init_grmhd_grid(char* fname, char* gridInName);
void load_grmhd_frame(char* fname);
double read_grmhd_time(const char* fname);
GrmhdGridStats grmhd_grid_stats();
size_t grmhd_primitive_count();
FloatCopyError copy_grmhd_primitives(float* output);
void interpolate_grmhd_primitives(
    const float* frame,
    const BhacStencil& stencil,
    std::array<double, NPRIM>& primitive);
int get_fluid_params_from_primitives(
    const std::array<double, 4>& X,
    const BhacStencil& stencil,
    const std::array<double, NPRIM>& primitive,
    fluid::State* modvar,
    const std::array<std::array<double, 4>, 4>& gdown,
    const std::array<std::array<double, 4>, 4>& gup);
int get_fluid_stencil(const std::array<double, 4>& X, int initial_igrid, BhacStencil& stencil);
int get_fluid_params_cached(const std::array<double, 4>& X, const BhacStencil& stencil,
    fluid::State* modvar,
    const std::array<std::array<double, 4>, 4>& gdown,
    const std::array<std::array<double, 4>, 4>& gup);

#endif // READ_H

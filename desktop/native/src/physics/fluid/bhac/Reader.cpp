// read.cpp
#define _CRT_SECURE_NO_WARNINGS

#include "Reader.h"
#include <cstdio>
#include <cmath>
#include <cstdlib>
#include <array>
#include <cstring>
#include <stdexcept>
#include <string>

#include "src/physics/Constants.h" // Physical constants and unit conversions
#include "src/physics/Model.h" // Model parameters
#include "src/physics/spacetime/Metric.h" // metric library


using namespace ModelConstants;  // Import the entire namespace
using namespace Constants;

// global variables
//double RHO_unit, U_unit, B_unit;
//double Ne_unit, Thetae_unit;

double**** p = nullptr;
double R0, a, Q, hslope;

double* neqpar = nullptr;

std::array<double, 4> stopx, startx, dx;   // Use std::array instead
double xprobmin[3], xprobmax[3];
double** Xcoord = nullptr;
double*** Xgrid = nullptr;
double*** Xbar = nullptr;

int block_size = 0, forest_size = 0, cells = 0, ndimini = 0;
int ng[3], * forest = nullptr, * nx = nullptr, nleafs = 0;
int N1 = 0, N2 = 0, N3 = 0;

int LFAC, XI;

struct block* block_info = nullptr;

struct BhacHeader {
    int nleafs = 0;
    int levmax = 0;
    int ndimini = 0;
    int ndir = 0;
    int nw = 0;
    int nws = 0;
    int neqpar = 0;
    int it = 0;
    double t = 0.0;
};

static bool grmhd_grid_ready = false;
static int cached_nw = 0;
static int cached_nws = 0;
static int cached_neqpar = 0;

static void read_exact(
    FILE* file,
    void* target,
    size_t size,
    size_t count,
    const char* context) {

    if (fread(target, size, count, file) != count) {
        throw std::runtime_error(
            std::string("Cannot read complete BHAC ") + context + ".");
    }
}

static void seek_exact(
    FILE* file,
    long offset,
    int origin,
    const char* context) {

    if (fseek(file, offset, origin) != 0) {
        throw std::runtime_error(
            std::string("Cannot seek in BHAC ") + context + ".");
    }
}


// ==================== Implementation ====================

static void clear_primitive_data() {
    if (p != nullptr) {
        for (int i = 0; i < NPRIM; i++) {
            if (p[i] == nullptr) continue;
            for (int j = 0; j <= N1; j++) {
                if (p[i][j] == nullptr) continue;
                for (int k = 0; k <= N2; k++) {
                    free(p[i][j][k]);
                }
                free(p[i][j]);
            }
            free(p[i]);
        }
        free(p);
        p = nullptr;
    }
}

static void clear_grmhd_grid() {
    if (Xgrid != nullptr) {
        for (int j = 0; j < nleafs; j++) {
            if (Xgrid[j] == nullptr) continue;
            for (int i = 0; i < cells; i++) {
                free(Xgrid[j][i]);
            }
            free(Xgrid[j]);
        }
        free(Xgrid);
        Xgrid = nullptr;
    }

    if (Xbar != nullptr) {
        for (int j = 0; j < nleafs; j++) {
            if (Xbar[j] == nullptr) continue;
            for (int i = 0; i < cells; i++) {
                free(Xbar[j][i]);
            }
            free(Xbar[j]);
        }
        free(Xbar);
        Xbar = nullptr;
    }

    free(block_info);
    block_info = nullptr;
    free(forest);
    forest = nullptr;
    free(neqpar);
    neqpar = nullptr;
    free(nx);
    nx = nullptr;

    block_size = 0;
    forest_size = 0;
    cells = 0;
    ndimini = 0;
    nleafs = 0;
    N1 = 0;
    N2 = 0;
    N3 = 0;
    cached_nw = 0;
    cached_nws = 0;
    cached_neqpar = 0;
    grmhd_grid_ready = false;
}

static void clear_grmhd_data() {
    clear_primitive_data();
    clear_grmhd_grid();
}

void init_storage() {
    p = (double****)malloc(NPRIM * sizeof(double***));
    for (int i = 0; i < NPRIM; i++) {
        p[i] = (double***)malloc((N1 + 1) * sizeof(double**));
        for (int j = 0; j <= N1; j++) {
            p[i][j] = (double**)malloc((N2 + 1) * sizeof(double*));
            for (int k = 0; k <= N2; k++) {
                p[i][j][k] = (double*)malloc((N3) * sizeof(double));
            }
        }
    }
}
//
void metric_dd(const std::array<double, 4>& X_u, std::array<std::array<double, 4>, 4>& g_dd) {
	auto gdown = MetricDown(X_u);
    LOOP_ij g_dd[i][j] = gdown[i][j];


}

void metric_uu(const std::array<double, 4>& X_u, std::array<std::array<double, 4>, 4>& g_uu) {
	auto gup = MetricUp(X_u);
    LOOP_ij g_uu[i][j] = gup[i][j];

}

double get_detgamma(double x, double y, double z) {
    std::array<double, 4> X_u = { 0., x, y, z };
    std::array<std::array<double, 4>, 4> g_dd;
    metric_dd(X_u, g_dd);

    double detgamma = g_dd[1][1] * (g_dd[2][2] * g_dd[3][3] - g_dd[3][2] * g_dd[2][3]) -
        g_dd[1][2] * (g_dd[2][1] * g_dd[3][3] - g_dd[3][1] * g_dd[2][3]) +
        g_dd[1][3] * (g_dd[2][1] * g_dd[3][2] - g_dd[2][2] * g_dd[3][1]);

#if (DEBUG)
    if (std::isnan(sqrt(detgamma))) {
        double R2 = x * x + y * y + z * z;
        double a2 = a * a;
        double r2 = (R2 - a2 + sqrt((R2 - a2) * (R2 - a2) + 4. * a2 * z * z)) * 0.5;
        double r_current = sqrt(r2);
        fprintf(stderr, "isnan detgam %e %e rc %e\n", sqrt(detgamma), detgamma, r_current);
        detgamma = 0;
        exit(1);
    }
#endif
    return sqrt(detgamma);
}

void new_index(int dims, int i, int* new_i, int* new_j, int* new_k, int ip, int jp, int kp) {
    if (dims == 1) {
        *new_i = 2 * (ip)+i;
        *new_j = 0;
        *new_k = 0;
    }
    if (dims == 2) {
        *new_i = 2 * (ip)+i % 2;
        *new_j = 2 * (jp)+i / 2;
        *new_k = 0;
    }
    if (dims == 3) {
        *new_i = 2 * (ip)+i % 2;
        *new_j = 2 * (jp)+((int)(i / 2.)) % 2;
        *new_k = 2 * (kp)+(int)(i / 4.);
    }
}

void read_node(FILE* file_id, int* igrid, int* refine, int ndimini, int level,
    int ind_i, int ind_j, int ind_k) {
    int buffer_i[1], leaf;
    read_exact(file_id, buffer_i, sizeof(int), 1, "forest node");
    leaf = buffer_i[0];

    if (leaf) {
        (*igrid)++;
        int i = (*igrid);
        if (i > forest_size) {
            forest = (int*)realloc(forest, i * sizeof(int));
            forest_size++;
        }
        if (i > block_size) {
            block_info = (struct block*)realloc(block_info, i * sizeof(struct block));
            block_size++;
        }
        forest[forest_size - 1] = 1;
        block_info[block_size - 1].ind[0] = ind_i;
        block_info[block_size - 1].ind[1] = ind_j;
        block_info[block_size - 1].ind[2] = ind_k;
        block_info[block_size - 1].level = level;
    }
    else {
        (*refine)++;
        int i = (*igrid) + (*refine);
        if (i > forest_size) {
            forest = (int*)realloc(forest, i * sizeof(int) * 2);
            forest_size++;
        }
        forest[forest_size - 1] = 0;
        for (int ich = 0; ich < (int)pow(2, ndimini); ich++) {
            int cind_j, cind_i, cind_k;
            new_index(ndimini, ich, &cind_i, &cind_j, &cind_k, ind_i, ind_j, ind_k);
            read_node(file_id, igrid, refine, ndimini, level + 1, cind_i, cind_j, cind_k);
        }
    }
}

void calc_coord_bar(double* X, double* dxc_block, double* Xbar) {
    double coef_1D[3] = { 1., 4., 1. };
    double coef_2D[3][3], coef_3D[3][3][3];
    double is[3] = { -1., 0., 1. };
    double js[3] = { -1., 0., 1. };
    double ks[3] = { -1., 0., 1. };

    for (int i = 0; i < 3; i++)
        for (int j = 0; j < 3; j++)
            coef_2D[i][j] = coef_1D[i] * coef_1D[j];
    for (int i = 0; i < 3; i++)
        for (int j = 0; j < 3; j++)
            for (int k = 0; k < 3; k++)
                coef_3D[i][j][k] = coef_2D[i][j] * coef_1D[k];

    double norm = 0, xbar = 0, ybar = 0, zbar = 0, detgamma;
    for (int k = 0; k < 3; k++) {
        for (int j = 0; j < 3; j++) {
            for (int i = 0; i < 3; i++) {
                detgamma = get_detgamma(X[0] + dxc_block[0] / 2. * is[i],
                    X[1] + dxc_block[1] / 2. * js[j],
                    X[2] + dxc_block[2] / 2. * ks[k]);
                norm += detgamma * coef_3D[i][j][k];
                xbar += detgamma * coef_3D[i][j][k] * (X[0] + dxc_block[0] / 2. * is[i]);
                ybar += detgamma * coef_3D[i][j][k] * (X[1] + dxc_block[1] / 2. * js[j]);
                zbar += detgamma * coef_3D[i][j][k] * (X[2] + dxc_block[2] / 2. * ks[k]);
            }
        }
    }

    norm *= (dxc_block[0] / 6.0) * (dxc_block[1] / 6.0) * (dxc_block[2] / 6.0);
    xbar *= (dxc_block[0] / 6.0) * (dxc_block[1] / 6.0) * (dxc_block[2] / 6.0) / norm;
    ybar *= (dxc_block[0] / 6.0) * (dxc_block[1] / 6.0) * (dxc_block[2] / 6.0) / norm;
    zbar *= (dxc_block[0] / 6.0) * (dxc_block[1] / 6.0) * (dxc_block[2] / 6.0) / norm;

    Xbar[0] = xbar;
    Xbar[1] = ybar;
    Xbar[2] = zbar;

#if (DEBUG)
    if (std::isnan(Xbar[0])) {
        fprintf(stderr, "isnan in calc_coord_bar %e %e %e %e\n", Xbar[0], Xbar[1], Xbar[2], norm);
        Xbar[0] = 0; Xbar[1] = 0; Xbar[2] = 0;
        exit(1);
    }
#endif
}

void calc_coord(int c, int* nx, int ndimini, double* lb, double* dxc_block, double* X) {
    int local_ig[3];
    local_ig[0] = (int)((c % nx[0]));
    local_ig[1] = (int)(fmod(((double)c) / ((double)nx[0]), (double)nx[1]));
    if (ndimini == 3) {
        local_ig[2] = (int)(((double)c) / ((double)nx[0] * nx[1]));
    }
    for (int i = 0; i < ndimini; i++) {
        X[i] = lb[i] + (local_ig[i] + 0.5) * dxc_block[i];
    }
    if (std::isnan(X[0])) {
        fprintf(stderr, "isnan in calccoord %lf %d %lf %lf\n", lb[0], local_ig[0], dxc_block[0], ((double)c) / (nx[0] * nx[1]));
        exit(1);
    }
}

double get_r(const std::array<double, 4>& X_u) {
    if constexpr (metric == CKS)
    {
        double R2 = X_u[1] * X_u[1] + X_u[2] * X_u[2] + X_u[3] * X_u[3];
        double a2 = a * a;
        double r2 = (R2 - a2 + sqrt((R2 - a2) * (R2 - a2) + 4. * a2 * X_u[3] * X_u[3])) * 0.5;
        return sqrt(r2);
    }
    else if constexpr (metric == MKSBHAC)
    {
        return  exp(X_u[1]);
    }

}

void convert2prim(std::array<double, 8>& prim, double** conserved, int c, double X[3], double Xgrid[3], double dxc[3]) {
    std::array<double, 4> X_u = { 0., X[0], X[1], X[2] };
    std::array<std::array<double, 4>, 4> g_dd, g_uu;
    metric_dd(X_u, g_dd);
    metric_uu(X_u, g_uu);

    double r_current = get_r(X_u);
    if (r_current < 1.00) return;

    double BS = conserved[S1][c] * conserved[B1][c] + conserved[S2][c] * conserved[B2][c] + conserved[S3][c] * conserved[B3][c];
    double Bsq = 0;
    std::array<double, 4> B_d = { 0.,0.,0.,0. };
    std::array<double, 4> S_u = { 0.,0.,0.,0. };

    // Spatial partial contravariant metric (for boosting S_i)
    std::array<std::array<double, 4>, 4> gamma;
    for (int i = 1; i < 4; i++)
        for (int j = 1; j < 4; j++)
            gamma[i][j] = g_uu[i][j] + g_uu[0][i] * g_uu[0][j] / (-g_uu[0][0]);

    for (int j = 1; j < 4; j++) {
        for (int i = 1; i < 4; i++) {
            S_u[j] += gamma[i][j] * conserved[S1 + i - 1][c];
            B_d[j] += g_dd[i][j] * conserved[B1 + i - 1][c];
        }
    }
    for (int i = 1; i < 4; i++) Bsq += B_d[i] * conserved[B1 + i - 1][c];

#if (DEBUG)
    if (std::isnan(BS) || std::isnan(Bsq)) {
        fprintf(stderr, "Bsq %e BS %e\n", Bsq, BS);
        fprintf(stderr, "B %e %e %e\n", conserved[B1][c], conserved[B2][c], conserved[B3][c]);
        fprintf(stderr, "V %e %e %e\n", conserved[S1][c], conserved[S2][c], conserved[S3][c]);
        LOOP_ij fprintf(stderr, "gij %d %d %e\n", i, j, g_dd[i][j]);
        exit(1);
    }
#endif

    prim[KRHO] = conserved[D][c] / conserved[LFAC][c];
    prim[UU] = (neqpar[0] - 1.) / neqpar[0] * (conserved[XI][c] / pow(conserved[LFAC][c], 2.) - prim[KRHO]) / (neqpar[0] - 1.);
    prim[U1] = S_u[1] / (conserved[XI][c] + Bsq) + conserved[B1][c] * BS / (conserved[XI][c] * (conserved[XI][c] + Bsq));
    prim[U2] = S_u[2] / (conserved[XI][c] + Bsq) + conserved[B2][c] * BS / (conserved[XI][c] * (conserved[XI][c] + Bsq));
    prim[U3] = S_u[3] / (conserved[XI][c] + Bsq) + conserved[B3][c] * BS / (conserved[XI][c] * (conserved[XI][c] + Bsq));
    prim[U1] *= conserved[LFAC][c];
    prim[U2] *= conserved[LFAC][c];
    prim[U3] *= conserved[LFAC][c];
    prim[B1] = BPOL * conserved[B1][c];
    prim[B2] = BPOL * conserved[B2][c];
    prim[B3] = BPOL * conserved[B3][c];

    if (prim[UU] < 0) {
        prim[UU] = (conserved[DS][c] / conserved[D][c]) * pow(prim[KRHO], neqpar[0] - 1) / (neqpar[0] - 1.);
        if (prim[UU] < 0) {
            // When the entropy inversion is still negative, the existing numerical lower limit is used and the correction process is not printed unit by unit.
            prim[UU] = 1e-14;
        }
    }

    double gVdotgV = 0;
    for (int i = 1; i < 4; i++)
        for (int j = 1; j < 4; j++)
            gVdotgV += g_dd[i][j] * prim[U1 + i - 1] * prim[U1 + j - 1];
    double gammaf = sqrt(gVdotgV + 1.);

#if (DEBUG)
    if (prim[UU] < 0) {
        fprintf(stderr, "U %e gam %e XI %e LFAC %e lor %e RHO %e\n", prim[UU], neqpar[0], conserved[XI][c], conserved[LFAC][c], gammaf, prim[KRHO]);
        exit(1);
    }
    if (std::isnan(gammaf)) {
        fprintf(stderr, "gVdotgV %e lfac %e lor %e\n", gVdotgV, conserved[LFAC][c], gammaf);
        fprintf(stderr, "lor %e gVdotgV %e lfac %e XI %e Bsq %e BS %e\n", gammaf, gVdotgV, conserved[LFAC][c], conserved[XI][c], Bsq, BS);
        fprintf(stderr, "xi? %e %e\n", conserved[LFAC][c] * conserved[LFAC][c] * prim[KRHO] * (1 + neqpar[0] * prim[UU] / prim[KRHO]), conserved[XI][c]);
        fprintf(stderr, "rc %e %e\n", r_current, (1. + sqrt(1. - a * a)));
        fprintf(stderr, "Xbar %e %e %e\n", X[0], X[1], X[2]);
        fprintf(stderr, "X %e %e %e\n", Xgrid[0], Xgrid[1], Xgrid[2]);
        fprintf(stderr, "dxc %e %e %e\n", dxc[0], dxc[1], dxc[2]);
        exit(1);
    }
#endif
}

static void read_bhac_metadata(FILE* file_id, BhacHeader& header, int** nx_out, double** neqpar_out) {
    double buffer[1];
    unsigned int buffer_i[1];
    long int offset;

    seek_exact(file_id, 0, SEEK_END, "frame metadata");
    offset = -40;
    seek_exact(file_id, offset, SEEK_CUR, "frame metadata");

    read_exact(file_id, buffer_i, sizeof(int), 1, "nleafs metadata");
    header.nleafs = buffer_i[0];
    read_exact(file_id, buffer_i, sizeof(int), 1, "levmax metadata");
    header.levmax = buffer_i[0];
    read_exact(file_id, buffer_i, sizeof(int), 1, "dimension metadata");
    header.ndimini = buffer_i[0];
    read_exact(file_id, buffer_i, sizeof(int), 1, "direction metadata");
    header.ndir = buffer_i[0];
    read_exact(file_id, buffer_i, sizeof(int), 1, "variable-count metadata");
    header.nw = buffer_i[0];
    read_exact(file_id, buffer_i, sizeof(int), 1, "staggered-count metadata");
    header.nws = buffer_i[0];
    read_exact(file_id, buffer_i, sizeof(int), 1, "parameter-count metadata");
    header.neqpar = buffer_i[0];
    read_exact(file_id, buffer_i, sizeof(int), 1, "iteration metadata");
    header.it = buffer_i[0];
    read_exact(file_id, buffer, sizeof(double), 1, "time metadata");
    header.t = buffer[0];

    offset = offset - (header.ndimini * 4 + header.neqpar * 8);
    seek_exact(file_id, offset, SEEK_CUR, "grid metadata");

    *nx_out = (int*)malloc(header.ndimini * sizeof(int));
    *neqpar_out = (double*)malloc(header.neqpar * sizeof(double));

    for (int k = 0; k < header.ndimini; k++) {
        read_exact(file_id, buffer_i, sizeof(int), 1, "grid-size metadata");
        (*nx_out)[k] = buffer_i[0];
    }
    for (int k = 0; k < header.neqpar; k++) {
        read_exact(file_id, buffer, sizeof(double), 1, "equation parameter");
        (*neqpar_out)[k] = buffer[0];
    }
}

static void validate_frame_metadata(const char* fname, const BhacHeader& header,
    const int* frame_nx, const double* frame_neqpar) {
    if (!grmhd_grid_ready) {
        fprintf(stderr, "GRMHD grid has not been initialized before loading %s\n", fname);
        exit(1);
    }

    bool mismatch = false;
    mismatch = mismatch || header.nleafs != nleafs;
    mismatch = mismatch || header.ndimini != ndimini;
    mismatch = mismatch || header.nw != cached_nw;
    mismatch = mismatch || header.nws != cached_nws;
    mismatch = mismatch || header.neqpar != cached_neqpar;

    if (header.ndimini == ndimini) {
        for (int k = 0; k < ndimini; k++) {
            mismatch = mismatch || frame_nx[k] != nx[k];
        }
    }

    if (header.neqpar == cached_neqpar) {
        for (int k = 0; k < cached_neqpar; k++) {
            double scale = 1.0 + fabs(neqpar[k]);
            mismatch = mismatch || fabs(frame_neqpar[k] - neqpar[k]) > 1e-12 * scale;
        }
    }

    if (mismatch) {
        fprintf(stderr, "BHAC grid metadata changed in %s; cached SMR grid cannot be reused.\n", fname);
        fprintf(stderr, "cached: nleafs=%d ndimini=%d nw=%d nws=%d neqpar=%d\n",
            nleafs, ndimini, cached_nw, cached_nws, cached_neqpar);
        fprintf(stderr, "frame : nleafs=%d ndimini=%d nw=%d nws=%d neqpar=%d\n",
            header.nleafs, header.ndimini, header.nw, header.nws, header.neqpar);
        exit(1);
    }
}

double read_grmhd_time(const char* fname) {
    FILE* file_id = fopen(fname, "rb");
    if (file_id == NULL) {
        fprintf(stderr, "Cannot open GRMHD frame header: %s\n", fname);
        return NAN;
    }

    BhacHeader header;
    int* frame_nx = nullptr;
    double* frame_neqpar = nullptr;
    read_bhac_metadata(file_id, header, &frame_nx, &frame_neqpar);
    free(frame_nx);
    free(frame_neqpar);
    fclose(file_id);
    return header.t;
}

void init_grmhd_grid(char* fname, char* gridInName) {
    FILE* file_id;
    long int offset;
    int nxlone[3];

    file_id = fopen(fname, "rb");
    if (file_id == NULL) {
        fprintf(stderr, "\nCan't open sim data file... Abort!\n");
        fflush(stderr);
        exit(1234);
    }
    else {
        fprintf(stdout, "Successfully opened %s.\nReading grid\n", fname);
        fflush(stdout);
    }

    clear_grmhd_data();

    BhacHeader header;
    int* file_nx = nullptr;
    double* file_neqpar = nullptr;
    read_bhac_metadata(file_id, header, &file_nx, &file_neqpar);

    nleafs = header.nleafs;
    ndimini = header.ndimini;
    cached_nw = header.nw;
    cached_nws = header.nws;
    cached_neqpar = header.neqpar;

    LFAC = cached_nw - 2;
    XI = cached_nw - 1;
    nx = file_nx;
    neqpar = file_neqpar;

    a = neqpar[NSPIN];
    if (metric != MKSN) Q = 0.0;
    Q = 0.0;

    FILE* inputgrid;
    if (metric == CKS)
        inputgrid = fopen("grid_cks.in", "r");
    else
        inputgrid = fopen(gridInName, "r");

    if (inputgrid == NULL) {
        fprintf(stderr, "Cannot read input grid file: %s\n", gridInName);
        exit(1);
    }

    char temp[100], temp2[100];
    fscanf(inputgrid, "%s %s %d", temp, temp2, &nxlone[0]);
    fscanf(inputgrid, "%s %s %d", temp, temp2, &nxlone[1]);
    if (ndimini == 3)
        fscanf(inputgrid, "%s %s %d", temp, temp2, &nxlone[2]);
    fscanf(inputgrid, "%s %s %lf", temp, temp2, &xprobmin[0]);
    fscanf(inputgrid, "%s %s %lf", temp, temp2, &xprobmin[1]);
    if (ndimini == 3)
        fscanf(inputgrid, "%s %s %lf", temp, temp2, &xprobmin[2]);
    fscanf(inputgrid, "%s %s %lf", temp, temp2, &xprobmax[0]);
    fscanf(inputgrid, "%s %s %lf", temp, temp2, &xprobmax[1]);
    if (ndimini == 3)
        fscanf(inputgrid, "%s %s %lf", temp, temp2, &xprobmax[2]);
    fscanf(inputgrid, "%s %s %lf", temp, temp2, &hslope);
    fclose(inputgrid);

    if (metric == MKSBHAC || metric == MKSN) {
        xprobmin[1] *= 2. * std::numbers::pi;
        xprobmin[2] *= 2. * std::numbers::pi;
        xprobmax[1] *= 2. * std::numbers::pi;
        xprobmax[2] *= 2. * std::numbers::pi;
    }

    ng[0] = ng[1] = ng[2] = 1;
    startx[1] = xprobmin[0];
    startx[2] = xprobmin[1];
    startx[3] = xprobmin[2];
    stopx[1] = xprobmax[0];
    stopx[2] = xprobmax[1];
    stopx[3] = xprobmax[2];

    cells = 1;
    for (int k = 0; k < ndimini; k++) cells *= nx[k];

    N1 = nleafs;
    N2 = cells;
    N3 = 1;
    if (nleafs != N1 || cells != N2 || 1 != N3) {
        fprintf(stderr, "wrong N1, N2, N3! %d!=%d %d!=%d %d!=%d", nleafs, N1, cells, N2, 1, N3);
    }

    long int nleafs_long = nleafs;
    long int size_block = cells * (cached_nw) * 8;
    long int stag = nleafs_long * (nx[0] + 1) * (nx[1] + 1) * (nx[2] + 1) * cached_nws * 8;
    offset = nleafs * size_block + stag;
    seek_exact(file_id, 0, SEEK_SET, "grid data");
    seek_exact(file_id, offset, SEEK_CUR, "grid data");

    for (int i = 0; i < ndimini; i++) ng[i] = nxlone[i] / nx[i];
    if (ndimini < 3) ng[2] = 1;

    int igrid = 0, refine = 0;
    block_info = (struct block*)malloc(0);
    forest = (int*)malloc(sizeof(int));
    fprintf(stdout, ".");

    int level = 1;
#if (SFC)
    // The SFC part is omitted and remains intact but not used. It is retained according to the original logic (0 when SFC is not defined)
    // In the actual code, the SFC macro is 0, so the else branch is taken.
#else
    for (int k = 0; k < ng[2]; k++) {
        for (int j = 0; j < ng[1]; j++) {
            for (int i = 0; i < ng[0]; i++) {
                read_node(file_id, &igrid, &refine, ndimini, level, i, j, k);
            }
        }
    }
#endif

    if (nleafs != igrid) {
        fprintf(stderr, "something wrong with grid dimensions\n");
        exit(1);
    }

    double* dx1 = (double*)malloc(ndimini * sizeof(double));
    double* dxc = (double*)malloc(ndimini * sizeof(double));
    for (int i = 0; i < ndimini; i++) {
        dx1[i] = (xprobmax[i] - xprobmin[i]) / ng[i];
        dxc[i] = (xprobmax[i] - xprobmin[i]) / nxlone[i];
    }

    Xgrid = (double***)malloc(nleafs * sizeof(double**));
    Xbar = (double***)malloc(nleafs * sizeof(double**));
    for (int j = 0; j < nleafs; j++) {
        Xgrid[j] = (double**)malloc(cells * sizeof(double*));
        Xbar[j] = (double**)malloc(cells * sizeof(double*));
        for (int i = 0; i < cells; i++) {
            Xgrid[j][i] = (double*)malloc(ndimini * sizeof(double));
            Xbar[j][i] = (double*)malloc(ndimini * sizeof(double));
        }
    }

    init_storage();
    fprintf(stdout, ".");

    for (int i = 0; i < nleafs; i++) {
        for (int n = 0; n < ndimini; n++) {
            block_info[i].lb[n] = xprobmin[n] + (block_info[i].ind[n]) * dx1[n] / pow(2., (double)block_info[i].level - 1.);
#if (DEBUG)
            if (std::isnan(block_info[i].lb[n])) {
                fprintf(stderr, "NaN %d %lf %d", i, pow(2, block_info[i].level - 1), block_info[i].level);
                exit(1);
            }
#endif
            block_info[i].dxc_block[n] = dxc[n] / (pow(2., (double)block_info[i].level - 1.));
            block_info[i].size[n] = nx[n];
        }

        int c;
#pragma omp parallel for schedule(static, 1)
        for (c = 0; c < cells; c++) {
            calc_coord(c, nx, ndimini, block_info[i].lb, block_info[i].dxc_block, Xgrid[i][c]);
            std::array<double, 4> X_u = { 0., Xgrid[i][c][0], Xgrid[i][c][1], Xgrid[i][c][2] };
            double r = get_r(X_u);
            if (r > 1.0) {
                calc_coord_bar(Xgrid[i][c], block_info[i].dxc_block, Xbar[i][c]);
            }
            else {
                for (int n = 0; n < ndimini; n++) Xbar[i][c][n] = Xgrid[i][c][n];
            }
#if (DEBUG)
            if (std::isnan(Xgrid[i][c][0])) {
                fprintf(stderr, "%d %d", c, i);
                exit(1);
            }
#endif
            if (i == (nleafs / 2) && c == 0) fprintf(stdout, ".");
        }
#pragma omp barrier
    }

    grmhd_grid_ready = true;

    free(forest);
    forest = nullptr;
    free(dx1);
    free(dxc);
    fclose(file_id);
    fprintf(stdout, "\nDone\n");
    fflush(stdout);
}

void load_grmhd_frame(char* fname) {
    double buffer[1];
    if (!grmhd_grid_ready) {
        fprintf(stderr, "GRMHD grid has not been initialized before loading %s\n", fname);
        exit(1);
    }

    FILE* file_id = fopen(fname, "rb");
    long int offset;

    if (file_id == NULL) {
        fprintf(stderr, "\nCan't open sim data file... Abort!\n");
        fflush(stderr);
        exit(1234);
    }
    else {
        fprintf(stdout, "Successfully opened %s.\nReading data\n", fname);
        fflush(stdout);
    }

    BhacHeader header;
    int* frame_nx = nullptr;
    double* frame_neqpar = nullptr;
    read_bhac_metadata(file_id, header, &frame_nx, &frame_neqpar);
    validate_frame_metadata(fname, header, frame_nx, frame_neqpar);
    free(frame_nx);
    free(frame_neqpar);

    double** values = (double**)malloc(cached_nw * sizeof(double*));
    for (int i = 0; i < cached_nw; i++) {
        values[i] = (double*)malloc(cells * sizeof(double));
    }

    seek_exact(file_id, 0, SEEK_SET, "frame payload");

    for (int i = 0; i < nleafs; i++) {
        for (int nw = 0; nw < cached_nw; nw++) {
            for (int c = 0; c < cells; c++) {
                read_exact(file_id, buffer, sizeof(double), 1, "frame payload");
                values[nw][c] = buffer[0];
            }
        }

        int c;
#pragma omp parallel for shared(values, p) schedule(static, 1)
        for (c = 0; c < cells; c++) {
            std::array<double, 8> prim = {};
            std::array<double, 4> X_u = { 0., Xgrid[i][c][0], Xgrid[i][c][1], Xgrid[i][c][2] };
            double r = get_r(X_u);
            if (r > 1.0) {
                convert2prim(prim, values, c, Xbar[i][c], Xgrid[i][c], block_info[i].dxc_block);
            }

            p[KRHO][i][c][0] = prim[KRHO];
            p[UU][i][c][0] = prim[UU];
            p[U1][i][c][0] = prim[U1];
            p[U2][i][c][0] = prim[U2];
            p[U3][i][c][0] = prim[U3];
            p[B1][i][c][0] = prim[B1];
            p[B2][i][c][0] = prim[B2];
            p[B3][i][c][0] = prim[B3];

            if (i == (nleafs / 2) && c == 0) fprintf(stdout, ".");
        }
#pragma omp barrier
        offset = (nx[0] + 1) * (nx[1] + 1) * (nx[2] + 1) * cached_nws * 8;
        seek_exact(file_id, offset, SEEK_CUR, "staggered frame payload");
    }

    for (int i = 0; i < cached_nw; i++) {
        free(values[i]);
    }
    free(values);
    fclose(file_id);
    fprintf(stdout, "\nDone\n");
    fflush(stdout);
}

//void set_units(double M_unit_) {
//    RHO_unit = M_unit_ / (pow(T_unit, 2) * L_unit) * ratio;
//    U_unit = RHO_unit;
//    B_unit = sqrt(4. * M_PI * RHO_unit);
//    Ne_unit = RHO_unit / ((PROTON_MASS + ELECTRON_MASS) * SPEED_OF_LIGHT * SPEED_OF_LIGHT);
//}

void lower_index(const std::array<double, 4>& X_u, const std::array<double, 4>& V_u, std::array<double, 4>& V_d,
    const std::array<std::array<double, 4>, 4>& g_dd) {
    for (int i = 0; i < NDIM; i++) V_d[i] = 0.;
    LOOP_ij V_d[i] += g_dd[i][j] * V_u[j];
}

static int find_igrid(const std::array<double, 4>& x, struct block* block_info, double*** Xc, int &igrid_c) {
    double small = 1e-12;
    std::array<double, 4> x_mod = x;

	//First check whether it is outside the range. If it is outside the range, it returns -1 directly.

    if (x_mod[1] > stopx[1] || x_mod[1] < startx[1] || x_mod[2] < startx[2] || x_mod[2] > stopx[2] || x_mod[3] < startx[3] || x_mod[3] > stopx[3]) {
        igrid_c = -1;
		return -1;
    };

	// Reuse the previous leaf block when it still contains the query point.

   if (igrid_c ==-1||x_mod[1] + small < block_info[igrid_c].lb[0] ||
        x_mod[1] + small > block_info[igrid_c].lb[0] + block_info[igrid_c].size[0] * block_info[igrid_c].dxc_block[0] ||
        x_mod[2] + small < block_info[igrid_c].lb[1] ||
        x_mod[2] + small > block_info[igrid_c].lb[1] + block_info[igrid_c].size[1] * block_info[igrid_c].dxc_block[1] ||
        x_mod[3] + small < block_info[igrid_c].lb[2] ||
        x_mod[3] + small > block_info[igrid_c].lb[2] + block_info[igrid_c].size[2] * block_info[igrid_c].dxc_block[2])
    {


	   // Otherwise search all leaf blocks for the one containing the query point.
        for (int igrid = 0; igrid < nleafs; igrid++) {
            if (x_mod[1] + small >= block_info[igrid].lb[0] &&
                x_mod[1] + small < block_info[igrid].lb[0] + block_info[igrid].size[0] * block_info[igrid].dxc_block[0] &&
                x_mod[2] + small >= block_info[igrid].lb[1] &&
                x_mod[2] + small < block_info[igrid].lb[1] + block_info[igrid].size[1] * block_info[igrid].dxc_block[1] &&
                x_mod[3] + small >= block_info[igrid].lb[2] &&
                x_mod[3] + small < block_info[igrid].lb[2] + block_info[igrid].size[2] * block_info[igrid].dxc_block[2]) {
                igrid_c = igrid;
            }
        }
    }


    return -1;
}

// Locate the cell containing coordinate x within the selected leaf block.
static int find_cell(const std::array<double, 4>& x, struct block* block_info, int igrid, double*** Xc) {
    int i = (int)((x[1] - block_info[igrid].lb[0]) / block_info[igrid].dxc_block[0]);
    int j = (int)((x[2] - block_info[igrid].lb[1]) / block_info[igrid].dxc_block[1]);
    int k = (int)((x[3] - block_info[igrid].lb[2]) / block_info[igrid].dxc_block[2]);

    if (i >= nx[0]) i = nx[0] - 1;
    if (j >= nx[1]) j = nx[1] - 1;
    if (k >= nx[2]) k = nx[2] - 1;

    int cell = i + j * block_info[igrid].size[0] + k * block_info[igrid].size[0] * block_info[igrid].size[1];
    return cell;
}

static void coefficients(const std::array<double, 4>& X, struct block* block_info, int igrid, int c, std::array<double, 4>& del) {
    double block_start[4];
    double block_dx[4];
    int i, j, k;

    block_start[0] = block_info[igrid].lb[0] + 0. * block_info[igrid].dxc_block[0];
    block_dx[0] = block_info[igrid].dxc_block[0];
    block_start[1] = block_info[igrid].lb[1] + 0. * block_info[igrid].dxc_block[1];
    block_dx[1] = block_info[igrid].dxc_block[1];
    block_start[2] = block_info[igrid].lb[2] + 0. * block_info[igrid].dxc_block[2];
    block_dx[2] = block_info[igrid].dxc_block[2];

    i = (int)((X[1] - block_start[0]) / block_dx[0] + 1000) - 1000;
    j = (int)((X[2] - block_start[1]) / block_dx[1] + 1000) - 1000;
    k = (int)((X[3] - block_start[2]) / block_dx[2] + 1000) - 1000;

    if (i < 0) del[1] = 0.;
    else if (i > nx[0] - 2) del[1] = 1.;
    else del[1] = (X[1] - ((i)*block_dx[0] + block_start[0])) / block_dx[0];

    if (j < 0) del[2] = 0.;
    else if (j > nx[1] - 2) del[2] = 1.;
    else del[2] = (X[2] - ((j)*block_dx[1] + block_start[1])) / block_dx[1];

    if (k < 0) del[3] = 0.;
    else if (k > nx[2] - 2) del[3] = 1.0;
    else del[3] = (X[3] - ((k)*block_dx[2] + block_start[2])) / block_dx[2];
}

int compute_c(int i, int j, int k) {
    return i + j * nx[0] + k * nx[0] * nx[1];
}

double interp_scalar(double** var, int c, const std::array<double, 4>& coeff) {
    double interp;
    int c_ip, c_jp, c_kp;
    int c_i, c_j, c_k = 0;
    double b1, b2, b3;
    int cindex[2][2][2];

    double del1 = coeff[1], del2 = coeff[2], del3 = coeff[3];
    if (del1 > 1 || del2 > 1 || del3 > 1 || del1 < 0 || del2 < 0 || del3 < 0)
        fprintf(stderr, "del[1] %e \n del[2] %e\n del[3] %e\n", del1, del2, del3);

    c_i = (int)((c % nx[0]));
    c_j = (int)(fmod(((double)c) / ((double)nx[0]), (double)nx[1]));
    if (ndimini == 3) {
        c_k = (int)(((double)c) / ((double)nx[0] * nx[1]));
    }

    c_ip = c_i + 1;
    c_jp = c_j + 1;
    c_kp = c_k + 1;

    if (c_ip >= nx[0]) c_ip = c_i;
    if (c_jp >= nx[1]) c_jp = c_j;
    if (c_kp >= nx[2]) c_kp = c_k;

    b1 = 1. - del1;
    b2 = 1. - del2;
    b3 = 1. - del3;

    cindex[0][0][0] = compute_c(c_i, c_j, c_k);
    cindex[1][0][0] = compute_c(c_ip, c_j, c_k);
    cindex[0][1][0] = compute_c(c_i, c_jp, c_k);
    cindex[0][0][1] = compute_c(c_i, c_j, c_kp);
    cindex[1][1][0] = compute_c(c_ip, c_jp, c_k);
    cindex[1][0][1] = compute_c(c_ip, c_j, c_kp);
    cindex[0][1][1] = compute_c(c_i, c_jp, c_kp);
    cindex[1][1][1] = compute_c(c_ip, c_jp, c_kp);

    interp = var[cindex[0][0][0]][0] * b1 * b2 +
        var[cindex[0][1][0]][0] * b1 * del2 +
        var[cindex[1][0][0]][0] * del1 * b2 +
        var[cindex[1][1][0]][0] * del1 * del2;

    interp = b3 * interp + del3 * (var[cindex[0][0][1]][0] * b1 * b2 +
        var[cindex[0][1][1]][0] * b1 * del2 +
        var[cindex[1][0][1]][0] * del1 * b2 +
        var[cindex[1][1][1]][0] * del1 * del2);
    return interp;
}

static std::array<double, 4> normalize_grid_position(const std::array<double, 4>& X) {
    std::array<double, 4> x_mod = X;

    if constexpr (metric == MKSBHAC || metric == MKSN)
    {
        if (x_mod[2] < 0.0) {
            x_mod[2] = -x_mod[2];
            x_mod[3] = std::numbers::pi + x_mod[3];
        };


        x_mod[3] = fmod(x_mod[3], 2.0 * std::numbers::pi);
        x_mod[2] = fmod(x_mod[2], std::numbers::pi);


        if (x_mod[3] < 0.0) x_mod[3] = 2.0 * std::numbers::pi + x_mod[3];

    }

    return x_mod;
}

int get_fluid_stencil(const std::array<double, 4>& X, int initial_igrid, BhacStencil& stencil) {
    std::array<double, 4> x_mod = normalize_grid_position(X);

    int igrid = initial_igrid;
    if (igrid < 0 || igrid >= nleafs) igrid = -1;
    find_igrid(x_mod, block_info, Xgrid, igrid);

    if (igrid == -1) {
        fprintf(stderr, "issues with finding igrid, too close to barrier, skipping... %e %e %e\n", x_mod[1], x_mod[2], x_mod[3]);
        return 0;
    }

    int c = find_cell(x_mod, block_info, igrid, Xgrid);
    std::array<double, 4> del = {};
    coefficients(x_mod, block_info, igrid, c, del);

    stencil.igrid = igrid;
    stencil.cell = c;
    for (int i = 0; i < 3; i++) {
        stencil.del[i] = del[i + 1];
        stencil.dx_local[i] = block_info[igrid].dxc_block[i];
    }

    return 1;
}

int get_fluid_params_cached(const std::array<double, 4>& X, const BhacStencil& stencil,
    fluid::State* modvar,
    const  std::array<std::array<double, 4>, 4>& g_dd,
    const  std::array<std::array<double, 4>, 4>& g_uu) {

    std::array<double, 4> del = { 0.0, stencil.del[0], stencil.del[1], stencil.del[2] };
    std::array<double, NPRIM> primitive = {};
    for (int variable = 0; variable < NPRIM; variable++) {
        primitive[variable] = interp_scalar(p[variable][stencil.igrid], stencil.cell, del);
    }
    return get_fluid_params_from_primitives(X, stencil, primitive, modvar, g_dd, g_uu);
}

GrmhdGridStats grmhd_grid_stats() {
    GrmhdGridStats stats;
    stats.leaf_blocks = static_cast<size_t>(nleafs);
    for (int axis = 0; axis < 3; axis++) {
        stats.cells_per_block_axis[axis] =
            nx == nullptr ? 0 : static_cast<size_t>(nx[axis]);
    }
    stats.cells_per_block = static_cast<size_t>(cells);
    stats.active_cells = stats.leaf_blocks * stats.cells_per_block;
    stats.primitive_values = stats.active_cells * static_cast<size_t>(NPRIM);
    return stats;
}

size_t grmhd_primitive_count() {
    return static_cast<size_t>(NPRIM) *
        static_cast<size_t>(nleafs) *
        static_cast<size_t>(cells);
}

FloatCopyError copy_grmhd_primitives(float* output) {
    FloatCopyError error;
    size_t cells_total = static_cast<size_t>(nleafs) * static_cast<size_t>(cells);
    for (int variable = 0; variable < NPRIM; variable++) {
        for (int igrid = 0; igrid < nleafs; igrid++) {
            for (int cell = 0; cell < cells; cell++) {
                size_t index = static_cast<size_t>(variable) * cells_total +
                    static_cast<size_t>(igrid) * static_cast<size_t>(cells) +
                    static_cast<size_t>(cell);
                double value = p[variable][igrid][cell][0];
                output[index] = static_cast<float>(value);
                double difference = std::abs(static_cast<double>(output[index]) - value);
                error.max_absolute = std::max(error.max_absolute, difference);
                if (value != 0.0) {
                    error.max_relative = std::max(
                        error.max_relative,
                        difference / std::abs(value));
                }
            }
        }
    }
    return error;
}

void interpolate_grmhd_primitives(
    const float* frame,
    const BhacStencil& stencil,
    std::array<double, NPRIM>& primitive) {

    int ci = stencil.cell % nx[0];
    int cj = (stencil.cell / nx[0]) % nx[1];
    int ck = stencil.cell / (nx[0] * nx[1]);
    int ip = std::min(ci + 1, nx[0] - 1);
    int jp = std::min(cj + 1, nx[1] - 1);
    int kp = std::min(ck + 1, nx[2] - 1);
    int index[2][2][2] = {
        {{compute_c(ci, cj, ck), compute_c(ci, cj, kp)},
         {compute_c(ci, jp, ck), compute_c(ci, jp, kp)}},
        {{compute_c(ip, cj, ck), compute_c(ip, cj, kp)},
         {compute_c(ip, jp, ck), compute_c(ip, jp, kp)}}
    };
    double weight[2][3] = {
        {1.0 - stencil.del[0], 1.0 - stencil.del[1], 1.0 - stencil.del[2]},
        {stencil.del[0], stencil.del[1], stencil.del[2]}
    };
    size_t cells_total = static_cast<size_t>(nleafs) * static_cast<size_t>(cells);
    size_t block_offset = static_cast<size_t>(stencil.igrid) * static_cast<size_t>(cells);
    for (int variable = 0; variable < NPRIM; variable++) {
        double value = 0.0;
        size_t variable_offset = static_cast<size_t>(variable) * cells_total + block_offset;
        for (int di = 0; di < 2; di++) {
            for (int dj = 0; dj < 2; dj++) {
                for (int dk = 0; dk < 2; dk++) {
                    value += static_cast<double>(frame[variable_offset + index[di][dj][dk]]) *
                        weight[di][0] * weight[dj][1] * weight[dk][2];
                }
            }
        }
        primitive[variable] = value;
    }
}

int get_fluid_params_from_primitives(
    const std::array<double, 4>& X,
    const BhacStencil& stencil,
    const std::array<double, NPRIM>& primitive,
    fluid::State* modvar,
    const std::array<std::array<double, 4>, 4>& g_dd,
    const std::array<std::array<double, 4>, 4>& g_uu) {

    std::array<double, 4> x_mod = normalize_grid_position(X);
    double rho = primitive[KRHO];
    double uu = primitive[UU];
    std::array<double, 4> Bp, V_u, gV_u;
    double gVdotgV;

    int igrid = stencil.igrid;
    //Get the size of the grid
    for (size_t i = 0; i < 3; i++)
    {
        (*modvar).dx_local[i] = stencil.dx_local[i];
    };

    (*modvar).n_e = rho * Ne_unit + 1e-6;

    Bp[1] = primitive[B1];
    Bp[2] = primitive[B2];
    Bp[3] = primitive[B3];

    gV_u[1] = primitive[U1];
    gV_u[2] = primitive[U2];
    gV_u[3] = primitive[U3];

    std::array<std::array<double, 4>, 4> gamma_dd;

    for (int i = 1; i < 4; i++)
        for (int j = 1; j < 4; j++)
            gamma_dd[i][j] = g_dd[i][j];

    std::array<double, 4> shift;
    for (int j = 1; j < 4; j++)
        shift[j] = g_uu[0][j] / (-g_uu[0][0]);
    double alpha = 1 / sqrt(-g_uu[0][0]);

    gVdotgV = 0.;
    for (int i = 1; i < NDIM; i++)
        for (int j = 1; j < NDIM; j++)
            gVdotgV += gamma_dd[i][j] * gV_u[i] * gV_u[j];

    double lfac = sqrt(gVdotgV + 1.);
    V_u[1] = gV_u[1] / lfac;
    V_u[2] = gV_u[2] / lfac;
    V_u[3] = gV_u[3] / lfac;

    modvar->U_u[0] = lfac / alpha;
    for (int i = 1; i < NDIM; i++)
        modvar->U_u[i] = V_u[i] * lfac - shift[i] * lfac / alpha;


	// Lower the four-velocity with the metric tensor g_dd.
    lower_index(x_mod, modvar->U_u, modvar->U_d, g_dd);

    modvar->B_u[0] = 0;
    for (int i = 1; i < NDIM; i++)
        for (int l = 1; l < NDIM; l++)
            modvar->B_u[0] += lfac * Bp[i] * (gamma_dd[i][l] * V_u[l]) / alpha;

    for (int i = 1; i < NDIM; i++)
        modvar->B_u[i] = (Bp[i] + alpha * modvar->B_u[0] * modvar->U_u[i]) / lfac;


	// Lower the magnetic-field four-vector with the metric tensor g_dd.
    lower_index(x_mod, modvar->B_u, modvar->B_d, g_dd);


    double Bsq = fabs(modvar->B_u[0] * modvar->B_d[0] +
        modvar->B_u[1] * modvar->B_d[1] +
        modvar->B_u[2] * modvar->B_d[2] +
        modvar->B_u[3] * modvar->B_d[3]) + 1e-6;

	// Calculate the magnetic field strength B in CGS units, including rescale
    modvar->B = sqrt(Bsq) * B_unit;

	double gam = neqpar[0];// adiabatic index
	const double beta_trans = Config::BETA0;

	modvar->beta = uu * (gam - 1.0) / (0.5 * (Bsq + 1e-6));// plasma beta
	double b2 = pow((modvar->beta / beta_trans), 2.);// Controls the smooth R-beta transition used to calculate sigma and theta_e.


	//modvar->sigma = modvar->B * modvar->B / (rho * RHO_unit + 1e-6);// magnetization parameter

    modvar->sigma = Bsq / rho;


    modvar->sigma_min = 1.0;

	// To calculate the electron temperature theta_e, an empirical formula is used here, and the specific form may need to be adjusted according to the actual situation.
    //The basic idea of this formula is to relate the electron temperature to the magnetic field strength and plasma parameters, so that the electron temperature can change reasonably under different physical conditions.

    const double Rhigh = R_HIGH, Rlow = R_LOW;
    double trat = Rhigh * b2 / (1. + b2) + Rlow / (1. + b2);
    double Thetae_unit = (MPoME) / (trat + 1.0);


    modvar->theta_e = ((uu * (gam - 1.0)) / rho) * Thetae_unit;

 /*   double xc = r * sin(X[2]) * cos(X[3]);
    double yc = r * sin(X[2]) * sin(X[3]);
    double rc = sqrt(xc * xc + yc * yc);*/

    /*fprintf(stderr, "r=%e B=%e n_e=%e theta_e=%e\n",
      r,  modvar->B , modvar->n_e, modvar->theta_e);*/

    return 1;
}

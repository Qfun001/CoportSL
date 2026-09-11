# CoportSL：偏振慢光辐射转移

[English](README.md) | 简体中文

CoportSL 是在原始 [CoportS](https://github.com/JieweiHuang/CoportS) 偏振 GRRT 代码基础上扩展的慢光成像框架，用于计算黑洞吸积流的偏振快光图像与混合慢光图像。

## 下载并运行 Windows 桌面端

$\quad \quad$多数 Windows 用户无需构建 CoportSL。打开 [GitHub Releases 页面](https://github.com/Qfun001/CoportSL/releases)，选择需要的版本，在 **Assets** 区域下载 `CoportSL.exe`，然后双击运行。该文件是适用于 64 位 Windows 10/11 的单文件便携应用，无需另行安装 Python 或 Visual Studio。GitHub 自动生成的源码压缩包只包含源文件；运行图形界面时应下载 `.exe` 资源。

$\quad \quad$输入准备、首次启动、语言切换、推荐计算流程、结果位置和常见问题见 [CoportSL 桌面端使用说明](USER_GUIDE-zh.md)。界面默认使用英文，可在“Settings > Language”中即时切换为简体中文。

$\quad \quad$当前可执行文件未进行商业代码签名，Windows SmartScreen 可能显示“未知发布者”。请确认文件来自官方 Releases 页面，并核对该版本公布的 SHA-256 校验和后再继续运行。

## 目录

- [下载并运行 Windows 桌面端](#下载并运行-windows-桌面端)
- [概述](#概述)
- [输入数据](#输入数据)
- [源码构建环境](#源码构建环境)
- [从源码构建](#从源码构建)
- [Windows 桌面端源码构建](#windows-桌面端源码构建)
- 计算流程
  - [1. 用 Flux 确定吸积率](#1-用-flux-确定吸积率)
  - [2. 快光成像](#2-快光成像)
  - [3. 慢光前置分析](#3-慢光前置分析)
  - [4. 慢光成像](#4-慢光成像)
  - [5. 时间对齐与绘图](#5-时间对齐与绘图)
  - [6. 性能基准](#6-性能基准)
- [辅助分析工具](#辅助分析工具)
- [结果目录结构](#结果目录结构)
- [源码结构](#源码结构)
- [验证与限制](#验证与限制)
- [引用、软件与数据可用性](#引用软件与数据可用性)
- [许可证与来源](#许可证与来源)

## 概述

完整计算流程通常为：

```text
Flux 确定吸积率
  -> 快光成像
  -> 慢光前置分析，确定慢光区域与有效时间窗口
  -> 慢光成像
  -> 快慢光时间对齐
  -> 绘图与误差分析
  -> 性能基准
```

`apps/`、`src/` 和 `tools/` 分别保存应用入口、公共科学实现与 Python 分析工具，`desktop/` 保存 Windows 图形界面及其打包配置。

成像程序缓存测地线、空间插值 stencil 与平行移动偏振基矢，并在多个 GRMHD 时间帧与观测频率之间复用。混合慢光仅在数据相关的选定区域做时间插值，其余区域使用基准时刻的单帧 GRMHD 数据。

结果身份由输入内容、物理与数值参数、区域定义及时间原点共同决定，不包含人工版本号。因此优化实现或提高精度不会仅因软件版本变化而使已有结果失效；是否重算应依据具体参数差异与误差证据判断。

## 源码构建环境

构建环境：

- Windows 10/11：Visual Studio 2022（“使用 C++ 的桌面开发”工作负载）、MSVC `v143`、C++20、OpenMP。
- Linux / WSL2：CMake 3.22 及以上，支持 C++20 与 OpenMP 的 GCC/Clang，以及 Ninja 或 Make。
- Python：命令行科学工具和 Windows 桌面端需要 3.10 及以上。

安装命令行绘图与后处理依赖（松散版本）：

```powershell
python -m pip install -r requirements.txt
```

使用或打包 Windows 桌面端时，还需安装桌面依赖：

```powershell
python -m pip install -r requirements-desktop.txt
```

## 输入数据

仓库不包含 GRMHD 数据，运行前需准备：

1. 包含 `dataNNNN.dat` 的 BHAC 数据目录，例如 `data1200.dat`、`data1201.dat`；
2. 与之匹配的静态网格文件 `grid_mks.in`；
3. 用于保存 Stokes CSV、分析结果与图像的输出目录。

所有 `dataNNNN.dat` 必须采用相同的固定 SMR 网格与 primitive 变量布局。程序启动时由活动流体后端自动发现整个输入目录，要求帧号连续、文件完整、帧头时间严格递增且等间隔；首末帧与时间间隔不再由用户填写。慢光在成像前只选择整个时间窗口均有输入数据支撑的安全基准帧，任一侧数据不足都会在计算开始前报错，而不是钳制到输入边界。

在 [apps/grrt/GRRTConfig.h](apps/grrt/GRRTConfig.h) 中设置真实绝对路径：

```cpp
inline const std::filesystem::path DATA = "D:/CoportSL-data/output";
inline const std::filesystem::path GRID = "D:/CoportSL-data/grid_mks.in";
inline const std::filesystem::path OUTPUT = "D:/CoportSL-data/result";
constexpr int FLUID_BACKEND = BHAC;
```

上述默认路径仅为示例，使用前需替换。Python BHAC 读取器按 AMR 叶块顺序整帧读取，机械硬盘通常使用单加载线程即可。

## 从源码构建

### Windows

建议用 Visual Studio 打开 `CoportSL.slnx`。解决方案只保留日常科研程序 `CoportSL`，且仅提供 x64 配置，以避免大内存任务误用 32 位程序。

在 [apps/RunConfig.h](apps/RunConfig.h) 中修改唯一的默认目标行，即可选择日常程序：

```cpp
#define COPORTSL_APP COPORTSL_GRRT
// 也可改为 COPORTSL_FLUX 或 COPORTSL_BENCHMARK。
```

将 `CoportSL` 设为启动项目后，可直接“生成并运行”。切换目标会使依赖该配置的源码重新编译。命令行构建并确认当前目标：

```powershell
msbuild .\CoportSL.vcxproj /p:Configuration=Release /p:Platform=x64
.\build\bin\x64\Release\CoportSL.exe --show-app
```

### Linux / WSL

使用根目录 `CMakeLists.txt`。配置一次后，不指定目标会构建三个可执行文件，也可用 `--target` 单独构建：

```bash
cmake -S . -B build/cmake-linux -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build/cmake-linux --parallel

cmake --build build/cmake-linux --target GRRT --parallel
cmake --build build/cmake-linux --target Flux --parallel
cmake --build build/cmake-linux --target Benchmark --parallel
```

可执行文件位于 `build/cmake-linux/bin/`。WSL 中 Windows 数据盘通常挂载在 `/mnt/` 下，运行前需把配置头中的 Windows 路径改为对应的 Linux 挂载路径；仅编译不要求路径实际存在。

### 输入检查

GRRT 提供只读输入检查（不创建结果目录，也不追踪光线或执行辐射转移），用于确认自动发现的帧范围、帧数、时间间隔与两级签名：

```powershell
.\build\bin\x64\Release\CoportSL.exe --inspect-input
```

## Windows 桌面端源码构建

$\quad \quad$本节面向需要从源码运行、打包或参与开发图形界面的贡献者。普通用户可以从 [GitHub Releases](https://github.com/Qfun001/CoportSL/releases) 下载 `CoportSL.exe`，并按照[桌面端使用说明](USER_GUIDE-zh.md)操作。

$\quad \quad$`desktop/` 提供 Windows 图形界面，通过 JSON 作业调用 GRRT、Flux 和 Benchmark 三个 Worker。界面可运行 Flux 定标、慢光前置分析、快慢光成像、区域误差、后处理、GRMHD 工具与性能基准。

构建 Worker 并启动源码版：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-desktop.txt
powershell -ExecutionPolicy Bypass -File .\desktop\packaging\build-workers.ps1
.\.venv\Scripts\python.exe -m desktop
```

构建单文件发布版：

```powershell
powershell -ExecutionPolicy Bypass -File .\desktop\packaging\build.ps1
```

$\quad \quad$完成的候选发布文件位于 `dist\CoportSL.exe`。发布版本前应启动该文件进行检查，记录 SHA-256 校验和，并把它作为名为 `CoportSL.exe` 的资源附加到对应 GitHub Release。

生成的 `build/`、`dist/` 和 `CoportSL-data/` 均为本地构建或运行内容，不纳入 Git。

## 1. 用 Flux 确定吸积率

正式成像前，通常先把 `RunConfig.h` 选为 `COPORTSL_FLUX`，用一段代表性快光结果估计平均光通量，并据此调节 [apps/flux/FluxConfig.h](apps/flux/FluxConfig.h) 中的 `MDOT`。

常用参数：

- `MDOT`：待定的物理吸积率，单位太阳质量/年。
- `TARGET_FLUX_JY`：目标平均光通量密度，默认 `0.66 Jy`。
- `NT0`、`NT1`、`DNT`：用于平均的帧范围与采样步长。
- `ELECTRON`、`OBS_TH`、`NU`、`NPIX`、`FOV`：影响平均光通量的模型与观测参数。
- `DISTANCE_PC`：源到观测者的距离，单位 pc。

运行：

```powershell
.\build\bin\x64\Release\CoportSL.exe
```

输出中的 `suggested_mdot_linear` 与 `suggested_mdot_sqrt` 只是下一次扫描的初值建议。由于吸收与法拉第项也随归一化变化，光通量通常不与 `MDOT` 严格成正比，修改后应重新运行 `Flux` 验证。

## 2. 快光成像

将 `RunConfig.h` 选为 `COPORTSL_GRRT` 后，四种 GRRT 任务由 [apps/grrt/GRRTConfig.h](apps/grrt/GRRTConfig.h) 中的单一枚举选择：

```cpp
constexpr Task TASK = Task::Fast;
```

常用正式成像参数：

- `ELECTRON`：电子分布模型。
- `NPIX`、`FOV`：图像分辨率与视场。
- `NU`：观测频率（Hz），不同频率需分别运行。
- `OBS_R`、`OBS_TH`、`OBS_PH`：观测者位置。
- `MBH`、`SPIN`、`MDOT`、`MDOT_SIM`：黑洞与吸积率参数。
- `R_LOW`、`R_HIGH`、`BETA0`：R–β 电子温度模型。

快光逐帧处理后端发现的全部输入快照。开始追踪光线前，程序先按 `TASK=fast`、`model_signature` 与完整 I/Q/U/V 文件清单查找最新完整结果；命中时打印结果路径并直接复用，若开启自动后处理则可在该目录补算图表。`DATA`、`GRID`、`OUTPUT` 只控制本次运行的读写位置，不进入结果签名。

运行：

```powershell
.\build\bin\x64\Release\CoportSL.exe
```

快光结果写入 `OUTPUT/fast/outputNNNN/`：

```text
OUTPUT/
└── fast/
    └── output0001/
        ├── status.txt
        ├── config.txt
        ├── I1000.csv
        ├── Q1000.csv
        ├── U1000.csv
        ├── V1000.csv
        └── ...
```

`fast`、`analysis`、`slow`、`region_error`、`benchmark` 与两类 `interp_err` 分别独立编号。程序只识别规范的 `outputNNNN` 目录；身份匹配且请求 CSV 完整时复用，不完整时 Fast/Slow 覆盖本次请求的整个帧范围，其余任务新建下一个编号。`status.txt` 记录路径与 `running`、`complete`、`failed` 审计历史，不参与完整性判定。

正式 `config.txt` 只记录可迁移的数值语义。自动发现的时间轴总会写出首末源帧号 `Input::NT0`、`Input::NT1`、首帧时间 `Input::T0` 与最小相邻时间间隔 `Input::DT`。对等间隔输入有

$$
t(n)=\mathrm{Input::T0}
 +(n-\mathrm{Input::NT0})\mathrm{Input::DT}.
$$

非等间隔输入另写 `Input::CADENCE=irregular`、`Input::FRAME_COUNT` 及每个已发现位置的 `Input::FRAME.<i>.INDEX/TIME`。源帧号允许缺号，软件按显式时间插值且不虚构缺失文件。配置不保存数据、网格或输出的绝对路径；`model_signature` 是 64 位十六进制 SHA-256 文本，由网格、首个快照内容、完整时间轴与公共数值参数共同决定。同一输入复制到其他磁盘或操作系统后签名不变，目录编号本身不表达模型或参数。

## 3. 慢光前置分析

慢光区域与有效时间窗口取决于 GRMHD 数据、电子模型、频率与观测方向，不能直接沿用其他配置得到的数值。单独运行前置分析：

```cpp
namespace Config {
constexpr Task TASK = Task::Analysis;
}
namespace Analysis {
constexpr double SAMPLE_DT = 10.0; // 单位 rg/c。
}
```

分析覆盖后端发现的完整时间轴，并按 `SAMPLE_DT` 选取物理时间样本；若常规步长未落在末帧，末帧仍会加入。等间隔输入要求 `SAMPLE_DT / Input::DT` 在浮点容差内为正整数；非等间隔输入对每个目标时刻选择不早于它的第一帧，并跳过重复选择。`REGION_TOLERANCES` 分别给出六类转移系数允许留在慢光区域外的贡献比例。

区域选择使用 $j_I$、$j_P$、$\alpha_I$、$\alpha_P$、$\rho_V$、$\rho_C$ 六类非负支撑幅度，其中

$$
j_P=\sqrt{j_Q^2+j_U^2+j_V^2},\qquad
\alpha_P=\sqrt{\alpha_Q^2+\alpha_U^2+\alpha_V^2},\qquad
\rho_C=\sqrt{\rho_Q^2+\rho_U^2}.
$$

每帧、每类系数先在区域间归一化，再对有效分析帧取平均；Suggest 对每类系数按平均贡献降序累计到容限要求，最后取六类区域并集。区域偏移直方图使用整数 `frame_offset` 与仿射步长权重。`p90`、`p95`、`p99`、`p99.9` 是覆盖相应比例总仿射步长权重的最短连续有符号时延区间，`full` 使用全部偏移的端点。

`analysis_signature` 在 `model_signature` 基础上加入分析方法、采样间隔、容限、区域定义与时间原点。程序只复用状态完整、签名一致且必要文件齐全的最新分析批次；绝对路径与文件修改时间不进入签名。

分析结果按批次写入 `OUTPUT/analysis/outputNNNN/`：

```text
OUTPUT/
└── analysis/
    └── output0001/
        ├── status.txt
        ├── config.txt
        ├── regions/
        │   ├── index.csv
        │   ├── <region_key>/
        │   │   ├── contribution.csv
        │   │   ├── offset_histogram.csv
        │   │   ├── time_span.csv
        │   └── ...
        └── suggest/
            ├── regions.txt
            ├── time_span.csv
            └── windows.csv
```

`regions/index.csv` 保存稳定键、物理标签与采样数；每个区域的 `contribution.csv` 保存逐帧六类绝对贡献，`offset_histogram.csv` 保存整数偏移与权重，`time_span.csv` 保存逐像素时间跨度。`suggest/regions.txt` 为建议区域键，`suggest/windows.csv` 保存五种精确窗口端点。

## 4. 慢光成像

慢光任务先按 `analysis_signature` 复用最新完整分析；无匹配时在同一进程内生成分析再继续成像。Suggest 使用分析建议，Manual 从共享命名集合中选择一个组合：

```cpp
namespace Config {
constexpr Task TASK = Task::Slow;
}
namespace SlowLight {
constexpr RegionMode REGION_MODE = RegionMode::Suggest;
constexpr Window WINDOW = Window::P99;
inline const std::vector<RegionSelection> REGION_SETS = {
    {"r20", {"region_000"}},
    {"r50", {"region_000", "region_001", "region_002"}},
};
constexpr std::string_view MANUAL_SET = "r50";
}
```

`REGION_SETS` 同时供 Manual 慢光与 RegionError 的手动模式使用。名称须唯一，键须属于当前 `SlowLight::REGION`，各集合允许重叠且不要求嵌套。正式窗口端点与安全输出范围在运行时由当前区域与输入时间轴计算。

运行：

```powershell
.\build\bin\x64\Release\CoportSL.exe
```

慢光结果写入 `OUTPUT/slow/outputNNNN/`：

```text
OUTPUT/
└── slow/
    └── output0001/
        ├── status.txt
        ├── config.txt
        ├── time_span.csv
        ├── I<frame>.csv
        ├── Q<frame>.csv
        ├── U<frame>.csv
        ├── V<frame>.csv
        └── ...
```

慢光配置以相对 `analysis_path` 引用分析，并记录 `analysis_signature`、选择模式、稳定区域键、窗口名与精确 `LEFT/RIGHT`。整个 `result` 目录复制到其他路径后引用仍有效。慢光区域内、窗口外的采样时刻取最近窗口端点，区域外使用基准帧；只有窗口两端均有输入时间轴支撑的基准帧才会输出。

区域截断误差使用独立任务，不污染前置分析：

```cpp
namespace Config {
constexpr Task TASK = Task::RegionError;
}
namespace RegionError {
constexpr int FRAME_STEP = 25;
}
```

程序从完整输入时间轴首帧开始，每隔 `FRAME_STEP` 帧取一个代表帧；未与步长对齐的末帧不额外加入，实际帧号写入 `config.txt`。一次任务按 `SlowLight::REGION_SETS` 的定义顺序扫描全部命名集合，对每个集合分别计算“关闭区域外发射”与“关闭区域外全部转移系数”，并以同帧完整快光为参考。每个集合写入 `region_error/outputNNNN/<set>/error.csv`，字段为 `frame,mode,I_error,Q_error,U_error,V_error`；根目录 `config.txt` 以 `RegionError::SETS` 与 `RegionError::SET.<set>` 保存顺序与区域键。四个分量统一以参考总 Stokes I 归一化；后处理跨子目录计算代表帧算术平均与样本标准差，不保存逐像素空间残差。

零发射区域使用齐次转移分支，不计算无贡献的源项积分。偏振基投影在调用反余弦前把浮点余弦限制到 `[-1,1]`，避免平行极限的舍入误差产生非有限 Q/U；RegionError 仍会严格检查参考图与截断图的所有 Stokes 像素，并在失败信息中报告帧、集合、模式、像素与分量。

## 5. 时间对齐与绘图

`Postprocess::RUN` 是 C++ 唯一的自动后处理开关。关闭时不启动 Python，也不创建 `plot/`；打开时数值任务先写 `status.txt=complete`，再调用固定入口：

```cpp
namespace Postprocess {
constexpr bool RUN = true;
}
```

也可对已完成的当前格式结果手工调用同一入口：

```powershell
python .\tools\postprocess.py D:\CoportSL-data\result\slow\output0001
```

固定产物：

- Analysis：单张 `plot/contribution.pdf`。
- Fast：`plot/flux.csv/.pdf`、`lp.csv/.pdf`、`beta2.csv/.pdf`。
- Slow：Fast 的三组产物，另加 `time_window.pdf`、`time_span.pdf`；按相同 `model_signature` 选择编号最大的完整快光，写根目录相对引用 `fast.txt` 与 `plot/time_alignment.csv`。
- RegionError：带代表帧标准差误差棒的 `plot/error.pdf` 及 `plot/error_summary.csv`。

自动 CSV 不重复保存可由 `config.txt` 推导的时间、像素数与总光强。`flux.csv` 字段为 `frame,F_nu_Jy`，`lp.csv` 为 `frame,local_linear_fraction,net_linear_fraction`，`beta2.csv` 为 `frame,beta2_abs,beta2_angle_deg`。Python 绘图根据 `Input::...` 恢复物理时间。

`fast.txt` 记录相对快光路径、应加到慢光时间轴上的时间平移、相关系数、搜索区间、最小重叠比例、实际重叠帧数与 `Input::DT`。找不到完整匹配快光时，慢光自身后处理仍成功，只跳过对齐。Python 失败只把 `plot/status.txt` 写为 `failed`，不会把已完成的 C++ 数值结果改为失败。

自动入口不生成 EVPA、逐帧 PNG 或视频；Fast/Slow 完成时会打印手工命令。手工入口默认同时生成 PNG 与 PDF：

```powershell
python .\tools\evpa_plot.py D:\CoportSL-data\result\slow\output0001
```

面向论文的跨批次比较、时间插值误差与 GRMHD 图由 `tools/run.py`、`tools/interp_err.py` 与 `tools/bhac_plot.py` 显式配置运行，参数均集中写在各脚本的 `configure_parameters()` 中。

## 6. 性能基准

`Benchmark` 的配置入口是 [apps/benchmark/BenchmarkConfig.h](apps/benchmark/BenchmarkConfig.h)，日常使用主要修改：

- `CORE_MODES`：本次测试唯一的物理核心组。
- `NPIX_LIST`：图像分辨率列表。
- `CORE_COUNTS`：物理核心数列表，每核固定一个 OpenMP 线程。

Benchmark 固定以 Thermal、230 GHz、$512^2$ 与 Shell 配置计算两级签名，要求 `OUTPUT/analysis` 中已存在签名与必要文件均匹配的完整前置分析。程序读取该分析的 Suggest 区域与 `p99` 精确窗口后才开始计时，不在性能测量中补算分析；因此在完整流程中 Benchmark 放在前置分析、快慢光与区域误差之后。

一次 Benchmark 运行只初始化一次固定网格，每个 `NPIX_LIST` 分辨率只构造一次光线几何、流体网格定位与慢光掩膜；每个 repeat 的快光活动帧或慢光 `FrameCache` 也只准备一次，供该分辨率下全部核心数只读复用。各核心数组合分别执行并计时辐射转移。

每次性能测试写入不可覆盖的 `OUTPUT/benchmark/outputNNNN/`，其中 `config.txt` 保存签名、Suggest 区域与窗口，`status.txt` 保存实际分析相对路径，`summary.csv` 保存扫描结果。[tools/benchmark.py](tools/benchmark.py) 从 `status.txt` 自动解析该分析，生成：

- `time.*`：成像耗时。
- `rate.*`：光线吞吐量。
- `grmhd_memory.*`：活动网格与单个 GRMHD 帧的结构化内存。
- `frame_cache.*`：自动选择结果与各原始区域在不同时间窗口下的慢光帧缓存估计。

`summary.csv` 精简为十一列，只保留传播类型、分辨率、物理核心数、实际网格点与采样点数、活动网格与单帧内存，以及逐帧更新与辐射转移时间的均值与标准差。CPU 型号与核心类型只在 `config.txt` 保存；光线数、图像内存、吞吐量与总时间由保留列推导。

## 辅助分析工具

[tools/interp_err.py](tools/interp_err.py) 集中验证两类时间线性插值误差。脚本读取 BHAC 帧，转换 primitive 变量，比较不同时间间隔下的插值误差与 $\sqrt{b^2}$ 的系统性削弱，输出 `b_interp.csv`、`error_dt.*`、`error_r.*`。

同一脚本还以原始快光时间间隔为基准，将较大时间间隔的结果插值回基准时刻：每个目标帧以参考图像总 Stokes I 归一化 I/Q/U/V 图像误差，再计算逐帧误差的算术平均与样本标准差，输出 `obs_interp_t.csv`、`obs_interp.csv`、`error_img.*`。其中 `obs_interp_t.csv` 保存每个目标帧的四个标量误差，`obs_interp.csv` 保存各时间间隔的均值与时间标准差；误差图以均值为数据点、时间标准差为误差棒。

运行前在 `configure_parameters()` 中集中配置路径与参数，再在 `main()` 中取消注释一行，选择 primitive 计算、primitive 绘图、I/Q/U/V 图像误差计算或图像误差绘图。默认运行只打印输入输出路径。

[tools/bhac_plot.py](tools/bhac_plot.py) 直接从 BHAC `dataNNNN.dat` 生成 GRMHD 平面图与体积加权 profile，不依赖 MATLAB `.mat` 中间文件。它复用 [tools/bhac/read_bhac.py](tools/bhac/read_bhac.py) 的机械盘连续读取与 [tools/bhac/c2p.py](tools/bhac/c2p.py) 的 primitive 转换，按当前 C++ BHAC 后端计算电子温度、磁化率、等离子体 beta、Bernoulli 参数与非热电子参数；旧工具的配色、色阶、视界、边界线、磁力线与大字号版式保留，图中时间改为直接读取帧头。

入口中的 `configure_parameters()` 使用绝对输入输出路径，默认示例输出为 `D:/CoportSL-data/result/GRMHDplot`。默认运行只打印路径，在 `main()` 中取消注释 `plot_frames(parameters)`、`plot_profiles(parameters)` 或 `make_quantity_movie(parameters, ...)` 后才执行相应任务。逐帧处理一次读取并计算所选全部物理量，避免机械盘重复寻道；AMR 一维统计使用 proper cell volume 权重。视频与拼图由公共的 [tools/lib/media.py](tools/lib/media.py) 生成。

## 结果目录结构

```text
result/
├── fast/
│   └── output0001/
│       └── plot/
├── slow/
│   └── output0001/
│       └── plot/
├── analysis/
│   └── output0001/
│       └── plot/
├── benchmark/
│   └── output0001/
│       └── plot/
├── interp_err/
│   ├── b_interp/output0001/
│   │   └── plot/
│   └── obs_interp/output0001/
│       └── plot/
├── GRMHDplot/
│   ├── xz/
│   ├── xy/
│   ├── xz_xy/
│   ├── profile/
│   └── movie/
└── comparison/
    ├── radius_scan/
    └── window_scan/
```

运行目录不编码物理参数；电子模型、观测角、频率、区域定义与窗口均以该目录的 `config.txt` 为准，对应的 Python 派生 CSV、图件与视频写入同一运行的 `plot/` 子目录。跨多个运行的控制变量扫描写入 `result/comparison/<name>/`。比较或发表结果时应同时记录运行编号与配置文件。

## 源码结构

```text
apps/                         统一应用入口、目标选择与各应用配置
├── Main.cpp
├── RunConfig.h
├── grrt/
├── flux/
└── benchmark/
src/
├── physics/
│   ├── Constants.h            基本物理常数和单位换算
│   ├── Model.h                模型选择和配置派生量
│   ├── fluid/                流体后端、网格定位和帧缓存
│   ├── spacetime/            度规、联络和测地线方程
│   └── transfer/             电子分布与偏振辐射转移
├── grrt/
│   ├── RayGeometry.*          光线几何
│   ├── StokesProjection.*     Stokes 屏幕投影
│   ├── fast/                 快光转移和区域统计
│   └── slow/                 慢光区域、时间窗口和前置分析
└── support/
    ├── RunDirectory.*         运行目录与输出管理
    └── numerics/             DP5 积分与线性代数
tools/                        Python 绘图和后处理
desktop/                      Windows 图形界面、Worker 覆盖层和打包配置
build/                        编译产物，不纳入 Git
```

## 验证与限制

- GitHub Actions 在 Windows 和 Linux 上构建命令行目标，并检查 Python 源码。
- 固定 SMR 网格只初始化一次；扫描期间每帧只重新加载流体变量。
- 快光、前置分析和慢光共用 `ray::RayGeometry` 与 `fluid::GridLocations`；慢光首次生成分析结果后不会重复追踪测地线或定位网格。
- `fluid::FrameCache` 管理通用时间窗口，BHAC 后端以 `float` 保存 primitive 帧载荷，并以 `double` 完成空间和时间插值。
- 当前运行时数据后端仍只有 BHAC 固定 SMR 数据，仓库不提供示例 GRMHD 数据。
- BHAC 网格、帧头和 primitive 载荷均检查精确读取长度、定位与关闭状态；截断、缺字段或不可读输入会在首次失败处终止。发布前的本地验证覆盖签名、结果兼容、CSV 完整性、运行锁、整段重算、帧范围和 RegionError 采样；测试文件不随公开源码发布。

## 引用、软件与数据可用性

- 当前软件版本为 `v0.6.5`。引用 CoportSL 时请使用 [CITATION.cff](CITATION.cff) 中的元数据。版本 `v0.6.5` 的归档地址为 [doi:10.5281/zenodo.22708025](https://doi.org/10.5281/zenodo.22708025)，全部版本的归档地址为 [doi:10.5281/zenodo.22708024](https://doi.org/10.5281/zenodo.22708024)。
- 源码仓库不包含论文计算所用的 GRMHD 原始快照；数据格式和输入要求见“输入数据”一节。
- 对论文所用 GRMHD 数据有合理需求时，请联系 Fan Zhou（`202631101012@mail.bnu.edu.cn`）商议获取方式。

## 许可证与来源

本项目继承原始 CoportS 的 GNU Affero General Public License v3.0，详见 [LICENSE.txt](LICENSE.txt)。分享或修改本项目时应保留原作者信息、源码来源和相同许可证要求。

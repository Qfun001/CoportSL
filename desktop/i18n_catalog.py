"""Simplified Chinese source strings and their English translations.

This catalog is consumed by :mod:`desktop.i18n`. Source strings stay in
Simplified Chinese so the existing interface can be restored exactly.
"""

from __future__ import annotations

ZH_TO_EN: dict[str, str] = {'个': 'a',
 '行': 'OK',
 '主题': 'Topic',
 '刷新': 'Refresh',
 '就绪': 'ready',
 '快光': 'Fast light',
 '日志': 'Log',
 '核心': 'core',
 '类型': 'Type',
 '设置': 'settings',
 ' 个。': '.',
 '发现 ': 'discover',
 '已完成': 'Completed',
 '慢光 ': 'slow light',
 '未设置': 'not set',
 '源距离': 'source distance',
 '网格：': 'Grid:',
 '进行中': 'In progress',
 '（帧 ': '(frame',
 '传播模型': 'propagation model',
 '列表项“': 'list item"',
 '区域误差': 'area error',
 '图件格式': 'Image format',
 '并行进程': 'parallel processes',
 '快光成像': 'fast light imaging',
 '慢光成像': 'slow light imaging',
 '控制变量': 'control variables',
 '数据路径': 'data path',
 '束流宽度': 'Beam width',
 '正式计算': 'formal calculation',
 '清单损坏': 'Broken manifest',
 '界面语言': 'interface language',
 '结果选择': 'Result selection',
 '观测图像': 'observation image',
 '观者时刻': 'viewer moment',
 '输出图件': 'Output drawing',
 '运行记录': 'Operation record',
 '通用参数': 'Common parameters',
 '黑洞质量': 'black hole mass',
 '；差异：': ';Difference:',
 'XZ 平面': 'XZ plane',
 '区域集合 ': 'area collection',
 '已生成图件': 'Drawing has been generated',
 '快慢光比较': 'Fast and slow light comparison',
 '未知图标：': 'Unknown icon:',
 '模拟吸积率': 'Simulated accretion rate',
 '真实源参数': 'true source parameters',
 '绘制磁力线': 'Draw magnetic field lines',
 '运行失败（': 'Run failed (',
 '”应为整数。': '"should be an integer.',
 '区域集合第 ': 'Regional Collection No.',
 '已生成物理量': 'Physical quantities have been generated',
 '当前已选择 ': 'Currently selected',
 '控制变量数值': 'control variable value',
 '数据适配参数': 'Data adaptation parameters',
 '未知核心组：': 'Unknown core group:',
 '清空运行记录': 'Clear running records',
 '目标通量密度': 'target flux density',
 '网格 h_s': 'Grid h_s',
 '运行性能基准': 'Run performance benchmarks',
 '非热电子分布': 'non-thermal electron distribution',
 ' 行缺少冒号。': 'The line is missing a colon.',
 '不连续（缺帧）': 'Discontinuity (missing frames)',
 '切换后立即生效': 'Effective immediately after switching',
 '已有任务在运行': 'There is already a task running',
 '径向分布下限。': 'Radial distribution lower limit.',
 '数值不能为空。': 'Value cannot be empty.',
 '校验进程失败：': 'Verification process failed:',
 '磁场强度 b²': 'Magnetic field strength b²',
 '绘制性能基准图': 'Plot performance benchmarks',
 '逐帧 EVPA': 'Frame-by-frame EVPA',
 '黑洞真实质量。': 'The true mass of a black hole.',
 ' 个后处理任务。': 'post-processing tasks.',
 'GRMHD 工具': 'GRMHD tools',
 '任务专属科研图件': 'Mission-specific scientific research drawings',
 '历史作业保留上限': 'Historical job retention upper limit',
 '尚未选择数据目录': 'No data directory selected yet',
 '慢光控制变量扫描': 'Slow light controlled variable scan',
 '无法保存作业配置': 'Unable to save job configuration',
 '物理质量密度 ρ': 'Physical mass density ρ',
 '观测图像插值误差': 'Observed image interpolation error',
 '频率 (GHz)': 'Frequency (GHz)',
 '）：必须为正数。': '): must be a positive number.',
 'GRMHD 分布图': 'GRMHD distribution map',
 '喷流、环境分别分层': 'Jets and environments are layered separately',
 '扫描结果目录失败：': 'Scan results directory failed:',
 '无法扫描数据目录：': 'Unable to scan data directory:',
 '深色 · 事件视界': 'Dark · Event Horizon',
 '绘制快慢光对比曲线': 'Draw fast and slow light contrast curves',
 '）：必须为正整数。': '): must be a positive integer.',
 ' 帧）：请补全缺帧。': 'Frame): Please complete the missing frame.',
 'GRMHD 模拟参数': 'GRMHD simulation parameters',
 '尚未检测处理器核心。': 'The processor core has not been detected yet.',
 '快光匹配：已扫描到 ': 'Fast light matching: scanned',
 '数值表达式过于复杂。': 'Numeric expression is too complex.',
 '生成任务专属科研图件': 'Generate task-specific scientific research drawings',
 '计算程序接受该作业。': 'The calculation program accepts the job.',
 '# 无法保存作业状态：': '# Unable to save job status:',
 '控制变量数值无法解析。': 'The control variable value cannot be parsed.',
 '无法读取通用默认配置：': 'Unable to read common default configuration:',
 '生成逐帧 EVPA 图': 'Generate frame-by-frame EVPA plots',
 '请至少选择一种分布图。': 'Please select at least one distribution plot.',
 'Lorentz 因子比值': 'Lorentz factor ratio',
 '射线积分的初始仿射步长。': 'The initial affine step size for ray integration.',
 '极角分布采用的径向下限。': 'The radial lower limit adopted for the polar angle distribution.',
 '请至少选择一种输出格式。': 'Please select at least one output format.',
 ' 个横轴数值（逗号分隔）：': 'horizontal axis values (comma separated):',
 '字段完整时复用已有 CSV': 'Reuse existing CSV when fields are complete',
 '所选作业没有可用日志文件。': 'There are no log files available for the selected job.',
 '积分器允许的最小仿射步长。': 'The minimum affine step allowed by the integrator.',
 '设置文件已损坏，已备份为 ': 'The settings file is corrupted and was backed up as',
 '），已回退到用户数据目录。': '), has fallen back to the user data directory.',
 '。请确认内部计算程序已构建。': '. Please confirm that the internal calculation program has been built.',
 '窗口关闭前正在终止当前任务…': 'Terminating current task before window closes...',
 '重复次数无效：必须为正整数。': 'Invalid number of repetitions: must be a positive integer.',
 '名称来自下方可编辑的区域集合。': 'Names come from the editable zone collection below.',
 '用于约束平均通量密度的目标值。': 'Target value used to constrain the average flux density.',
 '输入数据首帧或网格文件内容不同': 'The first frame or grid file content of the input data is different.',
 '快光匹配：当前选择不是慢光结果。': 'Fast light match: The current selection is not a slow light result.',
 '请先在结果表中选择一个完整结果。': 'Please select a complete result in the results table first.',
 '列表不能为空：请至少填写一个数值。': 'The list cannot be empty: please fill in at least one value.',
 '成像默认配置不可用，无法生成作业。': 'The imaging default configuration is not available and the job cannot be '
                      'generated.',
 '当前任务结束或取消后才能执行此操作。': 'This operation can only be performed after the current task is ended or '
                       'canceled.',
 ' 个结果；多选只适用于支持批量的任务。': 'results; multiple selection only applies to tasks that support batching.',
 '当前任务结束或取消后才能检查 CPU。': 'The CPU cannot be checked until the current task has ended or been '
                        'cancelled.',
 '未知内部 Python Worker：': 'Unknown internal Python Worker:',
 '请至少选择一种传播模型（快光或慢光）。': 'Please select at least one propagation model (fast light or slow light).',
 '频率列表不能为空：请至少填写一个频率。': 'Frequency list cannot be empty: please fill in at least one frequency.',
 '从数据与模型复制 GRMHD 与电子参数': 'Copy GRMHD and electronic parameters from data and models',
 '（输入签名一致，参数容差匹配；末位差异：': '(Input signatures are consistent, parameter tolerances match; '
                         'differences in last digits:',
 '自动模式缺少匹配结果时，会先运行前置分析。': 'When automatic mode lacks matching results, pre-analysis will be run '
                          'first.',
 '例如 10800, 11000, 11200': 'For example 10800, 11000, 11200',
 '执行表面积分的中心半径；必须在事件视界之外。': 'The center radius over which surface integration is performed; must be '
                           'outside the event horizon.',
 '限制偏振发射与吸收系数相对总强度系数的幅度。': 'Limits the magnitude of the polarized emission and absorption '
                           'coefficients relative to the total intensity coefficient.',
 'theme 必须是 dark 或 light。': 'theme must be dark or light.',
 '每组统计中剔除的前导帧数；这些帧仍会实际计算。': 'The number of leading frames to be excluded from each set of '
                            'statistics; these frames are still actually counted.',
 '起始帧，包含该帧；必须位于已发现的数据范围内。': 'Starting frame, including this frame; must be within the discovered '
                            'data range.',
 '每次作业使用一个核心组；可分别运行多次进行比较。': 'Each job uses one core group; it can be run multiple times for '
                             'comparison.',
 '结果根目录不存在或尚未设置；运行计算后会自动填充。': 'The result root does not exist or has not been set; it will be '
                              'automatically populated after running the calculation.',
 '<i>R</i>–β 电子温度模型的高磁化区温度比。': '<i>R</i>–β High magnetization region temperature ratio for the '
                               'electron temperature model.',
 '只有状态为 complete 的结果可以执行后处理。': 'Only results with a status of complete can be post-processed.',
 '非热电子参数必须满足 p_min 不大于 p_max。': 'Non-thermal electron parameters must satisfy p_min not greater '
                                'than p_max.',
 '尚未设置结果目录；运行时会在所选结果目录中匹配前置分析。': 'No results directory has been set; runtime will match the '
                                 'lookahead in the selected results directory.',
 '数据目录无效：请先在“数据”页选择 BHAC 数据目录。': 'The data directory is invalid: Please select the BHAC data '
                                 'directory on the "Data" page first.',
 '超过 σ<sub>max</sub> 的区域不产生辐射。': 'No radiation is produced in areas exceeding σ<sub>max</sub>.',
 '格式为“名称: key1, key2”；名称和键必须唯一。': 'The format is "name: key1, key2"; the name and key must be '
                                  'unique.',
 '测地线积分步长控制中的相对误差容限；对应内部字段 rtol。': 'Relative error tolerance in geodesic integration step control; '
                                   'corresponds to the internal field rtol.',
 '选择慢光区域时延分布的覆盖分位；决定安全输出范围和缓存跨度。': 'Select the coverage quantile of delay distribution in the '
                                   'slow-light area; determine the safe output range and cache '
                                   'span.',
 'last_parameters 必须是 JSON object。': 'last_parameters must be a JSON object.',
 '关闭窗口会终止当前任务，部分结果将保留为未完成状态。\n确定关闭吗？': 'Closing the window terminates the current task and leaves '
                                       'some results in an unfinished state.\n'
                                       'Are you sure you want to close it?',
 '该系数允许由所选慢光区域之外贡献的最大比例；用于生成自动区域建议。': 'This coefficient allows the maximum proportion of '
                                      'contributions from outside the selected slow-light area; '
                                      'used to generate automatic area suggestions.',
 '前置分析的快照采样间隔；必须是相邻 GRMHD 帧时间间隔的正整数倍。': 'Snapshot sampling interval for pre-analysis; must be a '
                                        'positive integer multiple of the time interval between '
                                        'adjacent GRMHD frames.',
 '注意：修改光线参数会改变模型签名和数值精度，已有结果的匹配状态需要重新检查。': 'Note: Modifying the light parameters will change the '
                                           'model signature and numerical accuracy, and the '
                                           'matching status of existing results needs to be '
                                           'rechecked.',
 '快光匹配：结果根目录中没有完整快光结果。请先用相同参数运行快光，然后点击刷新。': 'Flash Match: There are no complete flash results in '
                                            'the results root directory. Please run the flashlight '
                                            'with the same parameters first, then click Refresh.',
 '清空只删除软件作业目录中的配置、状态和日志，不会删除任何计算结果、图件或原始数据。': 'Clearing only deletes the configuration, status and '
                                              'logs in the software job directory, but does not '
                                              'delete any calculation results, drawings or '
                                              'original data.',
 '内部计算程序尚未到达安全停止边界。是否强制终止进程？\n强制终止可能留下未完成的当前帧文件。': 'The internal calculation program has not yet '
                                                   'reached the safe stopping boundary. Do you '
                                                   'want to force terminate the process?\n'
                                                   'Forced termination may leave the current frame '
                                                   'file unfinished.',
 '支持普通数值、6.5e9、3/4、pi 和带括号的简单四则运算；输入的表达式会保留到计算进程。': 'Supports ordinary numerical values, 6.5e9, '
                                                    '3/4, pi, and four simple arithmetic '
                                                    'operations with parentheses; entered '
                                                    'expressions are retained until the '
                                                    'calculation process.',
 '\n数据路径和各页面参数会自动恢复上次有效值；损坏时自动备份为 .broken.json 并恢复默认值。': 'The data path and each page parameter '
                                                         'will automatically restore the last '
                                                         'valid value; when damaged, it will '
                                                         'automatically back up to .broken.json '
                                                         'and restore the default value.',
 '并行数和图件格式对所有支持这些参数的勾选任务生效；任务会按依赖顺序串行执行，避免同时读取同一批大型文件。': 'The number of parallelism and image '
                                                         'format take effect for all checked tasks '
                                                         'that support these parameters; tasks '
                                                         'will be executed serially in dependent '
                                                         'order to avoid reading the same batch of '
                                                         'large files at the same time.',
 '区域误差按上方定义顺序一次扫描全部命名集合，分别关闭各集合外的发射系数或全部辐射转移系数，再与同帧完整快光图像比较。': 'The regional error scans all named '
                                                               'sets at once in the order defined '
                                                               'above, turns off the emission '
                                                               'coefficients or all radiation '
                                                               'transfer coefficients outside each '
                                                               'set, and then compares it with the '
                                                               'complete flash image of the same '
                                                               'frame.',
 '生成 flux.csv、lp.csv、beta2.csv 及对应曲线；复用 CSV 时不会再次读取全部 Stokes 图像。': 'Generate flux.csv, lp.csv, '
                                                                   'beta2.csv and corresponding '
                                                                   'curves; all Stokes images will '
                                                                   'not be read again when reusing '
                                                                   'CSV.',
 '数据适配参数只定义当前 GRMHD 模拟和电子模型；扫描参数定义需要比较的分辨率、物理核心数和帧范围。其余条件由 Benchmark 固定配置定义。': 'The data '
                                                                               'adaptation '
                                                                               'parameters only '
                                                                               'define the current '
                                                                               'GRMHD analog and '
                                                                               'electronic models; '
                                                                               'the scan '
                                                                               'parameters define '
                                                                               'the resolution, '
                                                                               'number of physical '
                                                                               'cores, and frame '
                                                                               'range to be '
                                                                               'compared. The '
                                                                               'remaining '
                                                                               'conditions are '
                                                                               'defined by the '
                                                                               'Benchmark fixed '
                                                                               'configuration.',
 '空间分区和命名集合由前置分析、慢光成像和区域误差共同使用；采样间隔与区域容差定义前置分析并进入分析签名，慢光成像和自动区域误差会匹配或生成相应分析。性能基准维护独立的数据适配参数，其余条件由 Benchmark 固定配置定义。': 'Spatial '
                                                                                                                      'partitioning '
                                                                                                                      'and '
                                                                                                                      'named '
                                                                                                                      'sets '
                                                                                                                      'are '
                                                                                                                      'used '
                                                                                                                      'by '
                                                                                                                      'pre-analysis, '
                                                                                                                      'slow-light '
                                                                                                                      'imaging, '
                                                                                                                      'and '
                                                                                                                      'area '
                                                                                                                      'errors; '
                                                                                                                      'the '
                                                                                                                      'sampling '
                                                                                                                      'interval '
                                                                                                                      'and '
                                                                                                                      'area '
                                                                                                                      'tolerance '
                                                                                                                      'define '
                                                                                                                      'the '
                                                                                                                      'pre-analysis '
                                                                                                                      'and '
                                                                                                                      'enter '
                                                                                                                      'the '
                                                                                                                      'analysis '
                                                                                                                      'signature, '
                                                                                                                      'and '
                                                                                                                      'slow-light '
                                                                                                                      'imaging '
                                                                                                                      'and '
                                                                                                                      'automatic '
                                                                                                                      'area '
                                                                                                                      'errors '
                                                                                                                      'will '
                                                                                                                      'match '
                                                                                                                      'or '
                                                                                                                      'generate '
                                                                                                                      'corresponding '
                                                                                                                      'analyses. '
                                                                                                                      'The '
                                                                                                                      'performance '
                                                                                                                      'benchmark '
                                                                                                                      'maintains '
                                                                                                                      'independent '
                                                                                                                      'data '
                                                                                                                      'adaptation '
                                                                                                                      'parameters, '
                                                                                                                      'and '
                                                                                                                      'the '
                                                                                                                      'remaining '
                                                                                                                      'conditions '
                                                                                                                      'are '
                                                                                                                      'defined '
                                                                                                                      'by '
                                                                                                                      'the '
                                                                                                                      'Benchmark '
                                                                                                                      'fixed '
                                                                                                                      'configuration.',
 '; }\n\n/* ---------- 输入控件 ---------- */\nQLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit, QTextEdit,\nQListWidget, QTableWidget, QTreeWidget {\n    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,\n        stop:0 ': '; '
                                                                                                                                                                                                                                            '}\n'
                                                                                                                                                                                                                                            '\n'
                                                                                                                                                                                                                                            '/* '
                                                                                                                                                                                                                                            '---------- '
                                                                                                                                                                                                                                            'Input '
                                                                                                                                                                                                                                            'control '
                                                                                                                                                                                                                                            '---------- '
                                                                                                                                                                                                                                            '*/\n'
                                                                                                                                                                                                                                            'QLineEdit, '
                                                                                                                                                                                                                                            'QSpinBox, '
                                                                                                                                                                                                                                            'QDoubleSpinBox, '
                                                                                                                                                                                                                                            'QComboBox, '
                                                                                                                                                                                                                                            'QPlainTextEdit, '
                                                                                                                                                                                                                                            'QTextEdit,\n'
                                                                                                                                                                                                                                            'QListWidget, '
                                                                                                                                                                                                                                            'QTableWidget, '
                                                                                                                                                                                                                                            'QTreeWidget '
                                                                                                                                                                                                                                            '{\n'
                                                                                                                                                                                                                                            '    '
                                                                                                                                                                                                                                            'background: '
                                                                                                                                                                                                                                            'qlineargradient(x1:0, '
                                                                                                                                                                                                                                            'y1:0, '
                                                                                                                                                                                                                                            'x2:0, '
                                                                                                                                                                                                                                            'y2:1,\n'
                                                                                                                                                                                                                                            '        '
                                                                                                                                                                                                                                            'stop:0',
 '帧': 'frame',
 '项': 'item',
 '任务': 'Task',
 '参数': 'parameters',
 '帧 ': 'frame',
 '慢光': 'slow light',
 '未知': 'unknown',
 '状态': 'Status',
 '结果': 'result',
 '连续': 'continuous',
 ' 帧，': 'frame,',
 '另有 ': 'Also',
 '帧扫描': 'frame scan',
 '成像屏': 'imaging screen',
 '束流角': 'Beam angle',
 '物理量': 'physical quantity',
 '耗时 ': 'Time consuming',
 '选择…': 'Choose…',
 '，共 ': ', a total of',
 '像素/边': 'pixels/edge',
 '前置分析': 'Preliminary analysis',
 '原始变量': 'original variable',
 '图像边长': 'Image side length',
 '当前页面': 'current page',
 '快光结果': 'Fast light results',
 '执行方式': 'Execution method',
 '插值误差': 'interpolation error',
 '时变曲线': 'time varying curve',
 '极角分布': 'polar angle distribution',
 '测量参数': 'Measurement parameters',
 '物理核心': 'physics core',
 '空间分区': 'spatial partitioning',
 '结果：—': 'Result: -',
 '观测频率': 'Observation frequency',
 '观者极角': "viewer's angle",
 '输出目录': 'Output directory',
 '退出码 ': 'exit code',
 '配置错误': 'Configuration error',
 '（快光 ': '(fast light',
 '；慢光 ': '; slow light',
 '作业 ID': 'Job ID',
 '可用区域键': 'Available area keys',
 '当前结果：': 'Current results:',
 '性能基准图': 'Performance Benchmark Chart',
 '样本帧数 ': 'Number of sample frames',
 '正在取消…': 'Canceling…',
 '磁化率 σ': 'Magnetic susceptibility σ',
 '观者方位角': "Viewer's azimuth",
 ' · 状态 ': '· Status',
 '任务仍在运行': 'Task is still running',
 '发射区外边界': 'outer boundary of launch zone',
 '帧扫描失败：': 'Frame scan failed:',
 '慢光前置分析': 'Slow light pre-analysis',
 '推荐计算流程': 'Recommended calculation process',
 '数据：未选择': 'Data: Not selected',
 '极向磁场占比': 'Poloidal magnetic field proportion',
 '电子分布模型': 'electron distribution model',
 '磁化参数上限': 'Magnetization parameter upper limit',
 '输入数据签名': 'Enter data signature',
 '运行正式计算': 'Run a formal calculation',
 '非热电子比例': 'non-thermal electron ratio',
 '# 作业文件：': '#Job file:',
 '与兼容快光对齐': 'Align with compatible flashlights',
 '匹配的前置分析': 'Matching pre-analysis',
 '帧序列不连续（': 'The frame sequence is not continuous (',
 '径向速度 vʳ': 'Radial velocity vʳ',
 '数据与模型准备': 'Data and model preparation',
 '检测处理器核心': 'Detect processor core',
 '结果目录不存在': 'The result directory does not exist',
 '网格与结果路径': 'Grid and result paths',
 '配置校验失败：': 'Configuration verification failed:',
 '默认结果目录：': 'Default results directory:',
 ' 写入正式计算页': 'Write official calculation page',
 'GRMHD 模拟': 'GRMHD simulation',
 '任务抽屉日志容量': 'Task drawer log capacity',
 '原始变量插值误差': 'Original variable interpolation error',
 '尚未选择结果目录': 'No results directory selected yet',
 '手动选择命名集合': 'Manual selection of named collections',
 '无法解析列表项“': 'Unable to parse list item"',
 '电子温度 T_e': 'Electronic temperature T_e',
 '观测插值误差绘图': 'Observation Interpolation Error Plot',
 '（旧版历史作业）': '(Old version of historical assignment)',
 '；已恢复默认值。': ';Default values have been restored.',
 'GRMHD 剖面图': 'GRMHD profile',
 '已提交（状态未知）': 'Submitted (status unknown)',
 '找不到内部计算程序': 'Internal calculator not found',
 '检查前置分析失败：': 'Check pre-analysis failed:',
 '电子数密度 n_e': 'electron number density n_e',
 '读取能力清单失败。': 'Failed to read capability list.',
 '；将请求终止进程。': '; will request the process to be terminated.',
 ' 行名称为空或重复：': 'Row name is empty or duplicate:',
 'GRRT 桌面工作站': 'GRRT Desktop Workstation',
 '已恢复上次结果目录：': 'Last result directory restored:',
 '慢光前置分析通用参数': 'Common parameters for slow light pre-analysis',
 '无法解析数值表达式“': 'Unable to parse numeric expression"',
 '生成积分观测量及曲线': 'Generate integral observations and curves',
 '非热电子幂律指数 p': 'Non-thermal electron power law exponent p',
 '吸积率与磁通量时变曲线': 'Accretion rate and magnetic flux time-varying curve',
 '数值表达式不能除以零。': 'Numeric expressions cannot be divided by zero.',
 '未知 GRRT 任务：': 'Unknown GRRT mission:',
 '空间分区与慢光分析参数': 'Spatial partitioning and slow light analysis parameters',
 '非热电子幂律指数上限。': 'Upper limit on non-thermal electron power law exponent.',
 '”：应为数值或简单分数。': '": Should be a numeric value or a simple fraction.',
 '当前结果目录尚不存在：\n': 'The current results directory does not yet exist:',
 '物理核心数列表不能为空。': 'The physical core number list cannot be empty.',
 '请选择一个完整慢光结果。': 'Please select a complete slow light result.',
 'JSON 顶层必须是对象：': 'The JSON top level must be an object:',
 '帧步长无效：必须为正整数。': 'Invalid frame step: must be a positive integer.',
 '最小洛伦兹因子 γ_min': 'Minimum Lorentz factor γ_min',
 '薄壳半宽必须小于积分半径。': 'The half-width of the thin shell must be smaller than the integrating radius.',
 '输出起始帧不能大于结束帧。': 'The output start frame cannot be larger than the end frame.',
 '）：起始帧不能大于结束帧。': '): The starting frame cannot be larger than the ending frame.',
 '当前选择有效，将按顺序执行 ': 'The current selection is valid and will be executed in sequence',
 '结果根目录不存在，无法打开。': 'As a result, the root directory does not exist and cannot be opened.',
 ' 不是完整结果，不能执行后处理': 'Not a complete result, post-processing cannot be performed',
 '成像屏所在事件的观者坐标时刻。': 'The viewer coordinate moment of the event where the imaging screen is '
                    'located.',
 '请至少勾选一个需要运行的任务。': 'Please check at least one task that needs to be run.',
 '进程未响应终止请求，强制结束。': 'The process did not respond to the termination request and was forced to '
                    'terminate.',
 '手动范围的结束输出帧，包含该帧。': 'The end output frame of the manual range, inclusive.',
 '逗号分隔整数；写入前去重并排序。': 'Comma-separated integers; deduplicated and sorted before writing.',
 '剖面径向范围必须满足下限小于上限。': 'The radial range of the profile must satisfy that the lower limit is '
                      'smaller than the upper limit.',
 '控制变量扫描需要至少两个慢光结果。': 'Controlled variable scans require at least two slow-light results.',
 '无法读取性能基准计算程序的默认配置：': 'Unable to read the default configuration of the performance benchmark '
                       'calculator:',
 ' 只能使用字母、数字、下划线和连字符。': 'Only letters, numbers, underscores, and hyphens may be used.',
 '当前任务结束或取消后才能清空运行记录。': 'The running record can only be cleared after the current task is ended or '
                        'canceled.',
 '核心组必须且只能选择一种物理核心类型。': 'A core group must select only one physical core type.',
 '输入检查（inspect-input）': 'Input inspection (inspect-input)',
 '默认为数据目录父目录下的 result': 'The default is result in the parent directory of the data directory.',
 '图像分辨率无效（camera.npix=': 'Invalid image resolution (camera.npix=',
 ' 个完整快光，但没有兼容结果。最接近的是 ': 'A complete flash, but no compatible results. The closest is',
 '设置根对象必须是 JSON object。': 'The settings root object must be a JSON object.',
 '包含 I/Q/U/V CSV 的快光结果目录': 'Quick results directory containing I/Q/U/V CSV',
 '电子温度低于该阈值时，局域辐射转移系数置零。': 'When the electron temperature is below this threshold, the local '
                           'radiative transfer coefficient is set to zero.',
 '黑洞无量纲自旋，允许范围为 [-1, 1]。': 'The black hole has a dimensionless spin, and the allowed range is [-1, '
                           '1].',
 '。请确认目录中存在 dataNNNN.dat。': '. Please confirm that dataNNNN.dat exists in the directory.',
 '没有找到匹配的 PNG 序列，请先生成分布图。': 'No matching PNG sequence found, please generate a distribution map '
                            'first.',
 'Worker 默认配置顶层不是 JSON 对象。': 'The default top-level configuration of Worker is not a JSON object.',
 'EVPA 对比需要时间对齐；请同时勾选快慢光对齐。': 'EVPA contrast requires time alignment; please check both fast and '
                              'slow light alignment.',
 '输入起始与结束时刻（逗号分隔，单位 r_g/c）：': 'Enter the start and end time (comma separated, unit r_g/c):',
 'EVPA 对比时刻（r<sub>g</sub>/c）': 'EVPA comparison time (r<sub>g</sub>/c)',
 '批作业中的每个任务都必须包含 kind 和 job。': 'Each task in a batch job must contain kind and job.',
 'XZ 图中标记喷流边界的 Bernoulli 等值线值。': 'Bernoulli contour values marking jet boundaries in XZ plots.',
 '已从“数据与模型”复制 GRMHD 模拟和电子模型参数。': 'GRMHD simulation and electronic model parameters have been '
                                 'copied from Data & Models.',
 '源距离；Flux 定标用它把辐射功率换算为观测通量密度。': 'Source distance; used by the Flux calibration to convert '
                                 'radiated power to observed flux density.',
 '静态网格文件无效：请选择存在的 grid_mks.in。': 'Invalid static grid file: Please select an existing grid_mks.in.',
 '；平均通量 <i>F</i><sub>ν</sub> = ': ';Average flux <i>F</i><sub>ν</sub> =',
 '测地线积分步长控制中的绝对误差容限；对应内部字段 atol。': 'Absolute error tolerance in geodesic integration step control; '
                                   'corresponds to the internal field atol.',
 'BHAC 网格 (grid_mks.in);;所有文件 (*)': 'BHAC Grid (grid_mks.in);;All files (*)',
 '找到多个网格候选：请在“网格与结果路径”中明确选择要使用的文件。': 'Multiple mesh candidates found: Please explicitly select the '
                                     'file to use in "Mesh and Result Path".',
 '手动范围的起始输出帧，包含该帧；关闭手动范围时自动输出全部可用帧。': 'The starting output frame of the manual range, including '
                                      'this frame; when the manual range is closed, all available '
                                      'frames are automatically output.',
 '手动范围的起始输出帧，包含该帧；范围必须落在当前时窗的安全基准帧内。': 'The starting output frame of the manual range, including '
                                       'this frame; the range must fall within the safe reference '
                                       'frame of the current time window.',
 '缺少静态网格文件 grid_mks.in：请通过“网格与结果路径”选择。': 'Missing static grid file grid_mks.in: please select via '
                                         'Grid and Result Path.',
 'Flux、前置分析和正式计算共用；性能基准仅在用户显式复制数据适配参数时更新。': 'Flux, pre-analysis and formal calculations are '
                                            'shared; the performance benchmark is only updated '
                                            'when the user explicitly copies the data adaptation '
                                            'parameters.',
 '每个物理核心固定使用一个 OpenMP 线程；不得超过所选核心组的可用核心数。': 'Fixed use of one OpenMP thread per physical core; '
                                            'must not exceed the number of available cores for the '
                                            'selected core group.',
 '度规 mksbhac 与流体后端 bhac 为当前唯一已接入能力，在作业中固定写入。': 'The metric mksbhac and the fluid backend bhac are '
                                               'currently the only connected capabilities and are '
                                               'fixedly written in the job.',
 '并行进程用于插值误差；GRMHD 图按帧顺序读取，避免多个进程同时争用大型 BHAC 文件。': 'Parallel processes are used for interpolation '
                                                   'errors; GRMHD maps are read in frame order to '
                                                   'avoid multiple processes competing for large '
                                                   'BHAC files simultaneously.',
 '电子 Lorentz 因子的比值 γ<sub>max</sub>/γ<sub>min</sub>。': 'The ratio of the electron Lorentz factors '
                                                      'γ<sub>max</sub>/γ<sub>min</sub>.',
 ' <i>M</i><sub>☉</sub> yr<sup>−1</sup><br>建议 Ṁ（线性）= ': '<i>M</i><sub>☉</sub> '
                                                        'yr<sup>−1</sup><br>Suggestion Ṁ (linear) '
                                                        '=',
 '从 n<sub>0</sub> 开始每隔 Δn 帧取样；未对齐的 n<sub>1</sub> 不额外加入。': 'Samples are taken every Δn frames '
                                                          'starting from n<sub>0</sub>; unaligned '
                                                          'n<sub>1</sub> are not added '
                                                          'additionally.',
 '控制 <i>R</i><sub>low</sub> 与 <i>R</i><sub>high</sub> 之间的过渡。': 'Controls the transition between '
                                                               '<i>R</i><sub>low</sub> and '
                                                               '<i>R</i><sub>high</sub>.',
 ';\n}\n\n/* ---------- 分组与卡片 ---------- */\nQGroupBox {\n    background: ': ';\n'
                                                                             '}\n'
                                                                             '\n'
                                                                             '/* ---------- '
                                                                             'Grouping and Cards '
                                                                             '---------- */\n'
                                                                             'QGroupBox {\n'
                                                                             '    background:',
 '真实源、屏幕、观者、光线积分、数值截断、前置分析和慢光区域使用 Benchmark 固定配置。缺少匹配前置分析时，计算程序会在性能计时之外自动生成。': 'Real source, '
                                                                               'screen, viewer, '
                                                                               'light integration, '
                                                                               'numerical '
                                                                               'truncation, front '
                                                                               'analysis and slow '
                                                                               'light areas use '
                                                                               'Benchmark fixed '
                                                                               'configurations. In '
                                                                               'the absence of '
                                                                               'matching '
                                                                               'pre-analysis, the '
                                                                               'calculation '
                                                                               'routine is '
                                                                               'automatically '
                                                                               'generated outside '
                                                                               'of the performance '
                                                                               'timing.',
 '; }\nQScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }\n\n/* ---------- 其他 ---------- */\nQTabWidget::pane { border: 1px solid ': '; '
                                                                                                                                                                 '}\n'
                                                                                                                                                                 'QScrollBar::add-line:horizontal, '
                                                                                                                                                                 'QScrollBar::sub-line:horizontal '
                                                                                                                                                                 '{ '
                                                                                                                                                                 'width: '
                                                                                                                                                                 '0; '
                                                                                                                                                                 '}\n'
                                                                                                                                                                 '\n'
                                                                                                                                                                 '/* '
                                                                                                                                                                 '---------- '
                                                                                                                                                                 'Others '
                                                                                                                                                                 '---------- '
                                                                                                                                                                 '*/\n'
                                                                                                                                                                 'QTabWidget::pane '
                                                                                                                                                                 '{ '
                                                                                                                                                                 'border: '
                                                                                                                                                                 '1px '
                                                                                                                                                                 'solid',
 '有': 'Yes',
 ' 帧': 'frame',
 '关于': 'About',
 '取消': 'Cancel',
 '帧号': 'Frame number',
 '成功': 'success',
 '末帧': 'last frame',
 '空闲': 'free',
 '编号': 'No.',
 '频率': 'Frequency',
 '分布图': 'Distribution map',
 '后处理': 'Post-processing',
 '帧：—': 'Frame: —',
 '数据：': 'Data:',
 '校验中': 'Checking',
 '真实源': 'source of truth',
 '视场角': 'field of view',
 '阶段：': 'Stage:',
 '任务参数': 'Task parameters',
 '光线积分': 'Ray integral',
 '勾选任务': 'Check tasks',
 '取消任务': 'Cancel task',
 '复制日志': 'Copy log',
 '径向分布': 'Radial distribution',
 '性能基准': 'Performance benchmark',
 '扫描参数': 'Scan parameters',
 '数值截断': 'numerical truncation',
 '时间窗口': 'time window',
 '查看日志': 'View log',
 '测量快光': 'Measuring fast light',
 '电子分布': 'electron distribution',
 '简体中文': 'Simplified Chinese',
 '网格：—': 'Grid: —',
 '观者位置': 'viewer position',
 '视频参数': 'Video parameters',
 '运行失败': 'Run failed',
 '选择文件': 'Select file',
 '首帧时刻': 'First frame time',
 '，实际 ': ', actual',
 ' 必须是 ': 'must be',
 '分布图参数': 'Distribution plot parameters',
 '基准与扫描': 'Benchmarks and scans',
 '快光匹配：': 'Fast light matching:',
 '数据与模型': 'Data and models',
 '核心组选择': 'core group selection',
 '正在运行：': 'Running:',
 '积分观测量': 'Integral observed quantity',
 '计算并绘图': 'Calculate and plot',
 'XY 截面图': 'XY section view',
 '偏振转移截断': 'polarization transfer cutoff',
 '后处理 · ': 'Post-processing ·',
 '幂律指数上限': 'upper limit of power law exponent',
 '打开作业目录': 'Open job directory',
 '数值表达式“': 'numeric expression"',
 '无法写入日志': 'Unable to write to log',
 '检查当前设置': 'Check current settings',
 '电子温度下限': 'Electronic temperature lower limit',
 '等离子体 β': 'Plasma β',
 '运行勾选任务': 'Run check task',
 '通用输出参数': 'Common output parameters',
 '（历史作业）': '(History assignment)',
 'EVPA 视频': 'EVPA video',
 '使用线性建议值': 'Use linear recommendations',
 '只重绘已有误差': 'Only redraw existing errors',
 '当前设置有效：': 'The current settings are valid:',
 '所选帧不存在：': 'The selected frame does not exist:',
 '数据路径和参数': 'Data paths and parameters',
 '浅色 · 星光': 'light color · starlight',
 '结果解析失败：': 'Result parsing failed:',
 '网格发现失败：': 'Grid discovery failed:',
 '配置校验通过：': 'Configuration verification passed:',
 '）。完整日志：': '). Full log:',
 ' 并恢复默认值。': 'and restore default values.',
 'GRMHD 视频': 'GRMHD videos',
 '使用平方根建议值': 'Use the square root suggested value',
 '原始变量误差绘图': 'Original variable error plot',
 '已恢复上次网格：': 'Last grid restored:',
 '数值表达式过长。': 'Numeric expression is too long.',
 '未知区域容限键：': 'Unknown area tolerance key:',
 '纵轴使用对数坐标': 'The vertical axis uses logarithmic coordinates',
 '软件目录不可写（': 'The software directory is not writable (',
 '（模型签名一致）': '(The model signature is consistent)',
 ' 完整性检查失败：': 'Integrity check failed:',
 '区域分区与命名集合': 'Region partitioning and named collections',
 '当前只提供简体中文': 'Currently only available in Simplified Chinese',
 '数值截断与发射区域': 'Numerical cutoff and launch area',
 '模拟静质量密度 ρ': 'Simulated static mass density ρ',
 '磁场俯仰角 η_B': 'Magnetic field pitch angle η_B',
 '读取运行记录失败：': 'Failed to read running records:',
 ' 个数值，实际得到 ': 'values, actually obtained',
 'GRMHD 原始变量': 'GRMHD original variable',
 '。请更换为可写目录。': '. Please change to a writable directory.',
 '已自动恢复上次使用的': 'Automatically restored last used',
 '按当前选中顺序输入 ': 'Enter in the currently selected order',
 '未检查匹配的前置分析': 'Preparation without checking for matching',
 '绘制慢光控制变量扫描': 'Plot slow light controlled variable sweep',
 '；改为终止直接进程。': '; Terminate the direct process instead.',
 '图像边长列表不能为空。': 'The image side length list cannot be empty.',
 '无法保存临时校验配置：': 'Unable to save temporary verification configuration:',
 '正式图像的单边像素数。': 'The number of pixels on one side of the formal image.',
 '至少需要一个区域集合。': 'At least one zone collection is required.',
 '非热电子幂律指数下限。': 'Lower bound on the non-thermal electron power law exponent.',
 '原始变量插值误差输出目录': 'Original variable interpolation error output directory',
 '有限体积薄壳的径向半宽。': 'Radial half-width of a thin shell with finite volume.',
 '观测图像插值误差输出目录': 'Observed image interpolation error output directory',
 '逗号分隔多个待比较间隔。': 'Commas separate multiple intervals to be compared.',
 'XZ + XY 双平面拼图': 'XZ + XY biplane puzzle',
 '当前页面没有统一的运行操作': 'There is no unified running operation on the current page',
 '未知 Worker 类型：': 'Unknown Worker type:',
 '观者到黑洞的径向坐标距离。': 'The radial coordinate distance from the observer to the black hole.',
 '运行当前 GRMHD 功能': 'Run the current GRMHD function',
 '）；<br>当前 Ṁ = ': ');<br>current Ṁ =',
 '数值表达式超出字段允许范围。': 'The numeric expression exceeds the allowed range of the field.',
 '请先在数据页选择结果根目录。': 'Please select the result root directory on the data page first.',
 '三类图件彼此独立，可同时生成。': 'The three types of drawings are independent of each other and can be '
                    'generated at the same time.',
 '时间范围应为两个逗号分隔数值。': 'The time range should be two comma separated values.',
 '请至少选择径向分布或极角分布。': 'Please select at least Radial Distribution or Polar Angular Distribution.',
 'CoportSL 作业配置 v1': 'CoportSL job configuration v1',
 '无法读取成像计算程序的默认配置：': 'Unable to read the default configuration of the imaging calculation program:',
 '\n当前使用软件同级的便携数据目录。': 'Currently using the portable data directory of the software peer.',
 '帧范围必须满足起始帧不大于结束帧。': 'The frame range must satisfy that the start frame is no larger than the end '
                      'frame.',
 '束流中心相对于局域磁场方向的夹角。': 'The angle between the beam center and the direction of the local magnetic '
                      'field.',
 '绘制指定时刻的快慢光 EVPA 对比': 'Draw EVPA comparison of fast and slow light at a specified moment',
 '从黑洞自旋轴正方向量起，界面以度输入。': 'The interface is entered in degrees, measured from the positive direction '
                        "of the black hole's spin axis.",
 '性能基准默认配置不可用，无法生成作业。': 'The performance benchmark default configuration is not available and the '
                        'job cannot be generated.',
 '目录中没有 dataNNNN.dat：': 'There is no dataNNNN.dat in the directory:',
 '输出帧范围必须同时填写起始帧和结束帧。': 'The output frame range must fill in both the start frame and the end '
                        'frame.',
 'Benchmark 标准默认配置不可用。': 'Benchmark standard default configuration is not available.',
 '快光匹配：慢光结果尚未完整，暂不能匹配。': 'Fast light matching: The slow light results are not complete yet and '
                         'cannot be matched yet.',
 '单步最大空间推进量相对局域网格尺度的比例。': 'The ratio of the maximum spatial advancement amount in a single step to '
                          'the local grid scale.',
 '选择包含 dataNNNN.dat 的目录': 'Select the directory containing dataNNNN.dat',
 '必须是可写的绝对目录；支持中文、空格与长路径': 'Must be a writable absolute directory; supports Chinese, spaces and '
                           'long paths',
 '自动发现 grid_mks.in，或手动选择': 'Automatically discover grid_mks.in, or select manually',
 '）；精确签名匹配由内部计算程序在运行时判定。': '); exact signature matches are determined at runtime by an internal '
                           'calculation routine.',
 '帧范围无效（flux.frame_start=': 'Invalid frame range (flux.frame_start=',
 '没有找到输入数据和模型参数兼容的完整快光结果。': 'No complete fast light results were found for which the input data '
                            'and model parameters were compatible.',
 '仅支持数值、科学计数法、括号和 +、-、*、/。': 'Only numeric values, scientific notation, parentheses and +, -, *, / '
                             'are supported.',
 '帧序列不连续：正式计算要求连续帧，请检查数据目录。': 'Frame sequence is not continuous: formal calculation requires '
                              'continuous frames, please check the data directory.',
 '运行完成后，这里显示各频率的平均通量与建议吸积率。': 'After the run is completed, the average flux and recommended '
                              'accretion rate for each frequency are displayed here.',
 '以 cos α 为变量的高斯分布标准差，因此无量纲。': 'The standard deviation of a Gaussian distribution with cos α as a '
                               'variable and is therefore dimensionless.',
 '输出吸积率、磁通量和无量纲磁通量的 CSV 与曲线。': 'Outputs CSV vs. curves of accretion rate, magnetic flux, and '
                               'dimensionless magnetic flux.',
 '任务已取消；中断的结果目录不会标记为 complete。': 'The task was canceled; the interrupted results directory will '
                                 'not be marked as complete.',
 '帧范围无效（benchmark.frame_start=': 'Invalid frame range (benchmark.frame_start=',
 '结束帧，包含该帧；不得小于 n<sub>0</sub>。': 'End frame, inclusive; must not be less than n<sub>0</sub>.',
 '从输入首帧开始每隔 Δn 帧取样；未对齐的末帧不额外加入。': 'Samples are taken every Δn frames starting from the first input '
                                  'frame; unaligned last frames are not added additionally.',
 '各项支持普通数值、6.5e9、3/4、pi 和简单四则运算。': 'Each item supports ordinary numerical values, 6.5e9, 3/4, pi '
                                   'and simple four arithmetic operations.',
 '用户请求取消，已发送安全停止标记，正在等待当前计算单元结束…': 'User requested cancellation, safe stop flag sent, waiting for '
                                   'current compute unit to end...',
 '未能从日志解析出 Flux 汇总；请查看任务抽屉中的完整日志。': 'Failed to parse Flux summary from log; see full log in task '
                                    'drawer.',
 '未在数据目录及其父目录找到 grid_mks.in，请手动选择。': 'grid_mks.in was not found in the data directory and its '
                                     'parent directory, please select manually.',
 '用于把模拟密度归一化到物理单位的吸积率；可由 Flux 定标约束。': 'Accretion rate used to normalize simulated density to '
                                      'physical units; can be constrained by Flux scaling.',
 '确定删除全部作业配置、状态和日志吗？\n科研计算结果和图件不会被删除。': 'Are you sure you want to delete all job configurations, '
                                        'status and logs?\n'
                                        'Scientific research calculation results and drawings will '
                                        'not be deleted.',
 '超过上限后自动删除最旧的作业 JSON、状态和日志；不会删除科研计算结果。': 'After exceeding the upper limit, the oldest job JSON, '
                                          'status and log will be automatically deleted; '
                                          'scientific research calculation results will not be '
                                          'deleted.',
 '任务专属图件只适用于 Analysis、Slow 和 RegionError。': 'Task-specific plots are only available for Analysis, '
                                            'Slow, and RegionError.',
 '射线进入 f<sub>H</sub> r<sub>H</sub> 内时终止追迹。': 'The tracing ends when the ray enters f<sub>H</sub> '
                                             'r<sub>H</sub>.',
 '文件名扫描只做初筛；点击顶部“检查当前设置”后，会同时检查路径、帧序列和计算程序配置。': 'File name scanning only performs preliminary '
                                                'screening; after clicking "Check Current '
                                                'Settings" at the top, the path, frame sequence, '
                                                'and calculation program configuration will be '
                                                'checked at the same time.',
 '结果目录中没有已完成的前置分析；自动模式会先执行前置分析，手动模式需要已有可解析的区域定义。': 'There is no completed pre-analysis in the '
                                                   'result directory; automatic mode will perform '
                                                   'pre-analysis first, and manual mode requires a '
                                                   'parsable region definition.',
 '输入值表示视场包含多少个 π rad；例如 0.015625 π rad 等于 π/64 rad。': 'The input value represents how many π rads '
                                                      'the field of view contains; for example, '
                                                      '0.015625 π rad is equal to π/64 rad.',
 '每行一个集合，例如：Omega1: north_000, south_000, non_jet_000': 'One set per line, for example: Omega1: '
                                                        'north_000, south_000, non_jet_000',
 '通用模型、观者、光线、空间分区、命名集合与分析容差均在“数据与模型”页设置；此处只保留任务选择和专属参数。': 'General models, viewers, lights, '
                                                          'spatial partitions, named sets, and '
                                                          'analysis tolerances are all set on the '
                                                          'Data & Model page; only task selection '
                                                          'and proprietary parameters remain here.',
 '用法：CoportSL.exe --internal-worker <kind> [--job] <job.json>': 'Usage: CoportSL.exe '
                                                                '--internal-worker <kind> [--job] '
                                                                '<job.json>',
 '只适用于慢光结果；对齐先于比较执行。曲线比较需要两者都已有积分观测量 CSV；EVPA 对比读取指定物理时刻附近的 Stokes 帧。': 'Applies to slow-light '
                                                                        'results only; alignment '
                                                                        'is performed before '
                                                                        'comparison. Curve '
                                                                        'comparisons require that '
                                                                        'both have an existing '
                                                                        'integrated observation '
                                                                        'CSV; EVPA comparison '
                                                                        'reads Stokes frames '
                                                                        'around the specified '
                                                                        'physical time.',
 '本页只设置定标抽样参数；以 π rad 表示的 <i>FOV</i>、电子分布、Ṁ、<i>D</i> 以及模型/观者/光线参数统一取自“数据与模型”页。': 'This page only '
                                                                                 'sets the '
                                                                                 'calibration '
                                                                                 'sampling '
                                                                                 'parameters; the '
                                                                                 '<i>FOV</i> '
                                                                                 'expressed in π '
                                                                                 'rad, electron '
                                                                                 'distribution, Ṁ, '
                                                                                 '<i>D</i> and '
                                                                                 'model/viewer/light '
                                                                                 'parameters are '
                                                                                 'all taken from '
                                                                                 'the "Data and '
                                                                                 'Model" page.',
 '\n偏振广义相对论辐射转移桌面软件\n\n许可证：GNU Affero General Public License v3.0\n主要组件：Qt/PySide6、PyInstaller、NumPy、SciPy、Matplotlib、OpenCV、nlohmann/json\n源码：对外发布时请在同一发布页提供本版本对应源码。': 'Polarization '
                                                                                                                                                                        'General '
                                                                                                                                                                        'Relativity '
                                                                                                                                                                        'Radiative '
                                                                                                                                                                        'Transfer '
                                                                                                                                                                        'Desktop '
                                                                                                                                                                        'Software\n'
                                                                                                                                                                        '\n'
                                                                                                                                                                        'License: '
                                                                                                                                                                        'GNU '
                                                                                                                                                                        'Affero '
                                                                                                                                                                        'General '
                                                                                                                                                                        'Public '
                                                                                                                                                                        'License '
                                                                                                                                                                        'v3.0\n'
                                                                                                                                                                        'Main '
                                                                                                                                                                        'components: '
                                                                                                                                                                        'Qt/PySide6, '
                                                                                                                                                                        'PyInstaller, '
                                                                                                                                                                        'NumPy, '
                                                                                                                                                                        'SciPy, '
                                                                                                                                                                        'Matplotlib, '
                                                                                                                                                                        'OpenCV, '
                                                                                                                                                                        'nlohmann/json\n'
                                                                                                                                                                        'Source '
                                                                                                                                                                        'code: '
                                                                                                                                                                        'When '
                                                                                                                                                                        'publishing '
                                                                                                                                                                        'to '
                                                                                                                                                                        'the '
                                                                                                                                                                        'outside '
                                                                                                                                                                        'world, '
                                                                                                                                                                        'please '
                                                                                                                                                                        'provide '
                                                                                                                                                                        'the '
                                                                                                                                                                        'source '
                                                                                                                                                                        'code '
                                                                                                                                                                        'corresponding '
                                                                                                                                                                        'to '
                                                                                                                                                                        'this '
                                                                                                                                                                        'version '
                                                                                                                                                                        'on '
                                                                                                                                                                        'the '
                                                                                                                                                                        'same '
                                                                                                                                                                        'release '
                                                                                                                                                                        'page.',
 '次': 'times',
 ' 项': 'item',
 '分箱': 'binning',
 '失败': 'failed',
 '平面': 'Plane',
 '排队': 'queue',
 '标题': 'Title',
 '签名': 'signature',
 '视频': 'video',
 '首帧': 'first frame',
 '剖面图': 'Sectional view',
 '已取消': 'Canceled',
 '快光 ': 'Fast light',
 '无量纲': 'dimensionless',
 '核心组': 'core group',
 '结果：': 'Result:',
 '运行中': 'Running',
 '需要 ': 'need',
 '任务失败': 'Task failed',
 '分布方向': 'Distribution direction',
 '区域模式': 'Regional mode',
 '命名集合': 'named collection',
 '已清理 ': 'Cleaned',
 '径向壳层': 'radial shell',
 '性能核心': 'performance core',
 '找不到 ': 'not found',
 '数据准备': 'Data preparation',
 '束流分布': 'Beam distribution',
 '正在取消': 'Canceling',
 '测量慢光': 'Measuring slow light',
 '电子模型': 'electronic model',
 '结束时间': 'end time',
 '能效核心': 'Energy efficiency core',
 '观者半径': 'viewer radius',
 '视频帧率': 'Video frame rate',
 '运行完成': 'Run completed',
 '选择目录': 'Select directory',
 '黑洞自旋': 'black hole spin',
 '，范围 ': ', range',
 'XY 平面': 'XY plane',
 '剖面图参数': 'Profile parameters',
 '完整性失败': 'Integrity failed',
 '快慢光对齐': 'Fast and slow light alignment',
 '无运行任务': 'No tasks to run',
 '检测失败：': 'Detection failed:',
 '物理吸积率': 'physical accretion rate',
 '结果根目录': 'Result root directory',
 '设置已保存': 'Settings saved',
 'XZ 截面图': 'XZ section view',
 '区域截断误差': 'area truncation error',
 '已发现网格：': 'Grids discovered:',
 '幂律指数下限': 'Power law exponential lower bound',
 '打开结果目录': 'Open results directory',
 '数据时间间隔': 'data interval',
 '无法打开目录': 'Unable to open directory',
 '比较时间范围': 'Compare time ranges',
 '电子温度模型': 'Electronic temperature model',
 '结果根目录：': 'Result root directory:',
 '运行当前任务': 'Run current task',
 '静态网格文件': 'Static mesh file',
 ' 个历史文件。': 'historical file.',
 'Flux 定标': 'Flux calibration',
 '内部程序错误：': 'Internal program error:',
 '尚未选择结果。': 'No results have been selected yet.',
 '径向分布上限。': 'Radial distribution upper limit.',
 '打开结果根目录': 'Open results root directory',
 '无效（实际值 ': 'invalid(actual value',
 '电子数密度下限': 'Lower limit of electron number density',
 '绘制喷流分界线': 'Drawing jet boundary lines',
 '运行 Flux': 'Run Flux',
 '阶段：正在取消': 'Stage: Canceling',
 ' Jy（标准差 ': 'Jy (standard deviation',
 ' 范围内的整数。': 'an integer within the range.',
 '”超出可用范围。': '"Out of available range.',
 '光线积分数值设置': 'Light integration value settings',
 '安全取消仍在等待': 'Safe cancellation still pending',
 '已把建议吸积率 ': 'The recommended accrual rate has been',
 '数据目录不存在：': 'Data directory does not exist:',
 '正在扫描帧文件…': 'Scanning frame files...',
 '自动采用分析建议': 'Automatically adopt analysis recommendations',
 '速度与分辨率扫描': 'Scan speed and resolution',
 '（进程异常结束）': '(Process ended abnormally)',
 'BHAC 数据目录': 'BHAC data directory',
 '取消标记路径不可用': 'Unmark path as unavailable',
 '手动指定输出帧范围': 'Manually specify the output frame range',
 '无法保存作业历史：': 'Unable to save job history:',
 '正在强制终止进程…': 'Forcefully terminating process...',
 '结果根目录不可写（': 'As a result the root directory is not writable (',
 '读取默认配置失败。': 'Failed to read default configuration.',
 ' 含当前分区未知键：': 'Contains unknown keys for the current partition:',
 'GRMHD 时变曲线': 'GRMHD time-varying curve',
 '图像边长列表项无效（': 'Image side length list item is invalid (',
 '平滑窗口必须为奇数。': 'The smoothing window must be an odd number.',
 '数值必须是有限实数。': 'Numeric values must be finite real numbers.',
 '生成 EVPA 视频': 'Generate EVPA video',
 '观者处望远镜与成像屏': "Telescope and imaging screen at observer's position",
 ' 的键为空或存在重复。': 'The key is empty or duplicated.',
 '快慢光 EVPA 对比': 'Fast and slow light EVPA comparison',
 '无法写入安全停止标记：': 'Unable to write safe stop flag:',
 '物理核心数列表项无效（': 'The physical core number list item is invalid (',
 '设置、作业与日志目录：': 'Settings, jobs and log directories:',
 ' Worker；已检查：': 'Worker; checked:',
 '复用已有 EVPA 图件': 'Reuse existing EVPA drawings',
 '极角分布采用的径向上限。': 'The radial upper limit adopted for the polar angle distribution.',
 '请至少选择一种图件格式。': 'Please select at least one image format.',
 '；建议 Ṁ（平方根）= ': ';Suggestion Ṁ (square root) =',
 '使用逗号分隔多个观测频率。': 'Use commas to separate multiple observation frequencies.',
 '当前页面没有需要检查的设置': 'There are no settings to check on the current page',
 '磁面角速度 Ω_B/Ω_H': 'Magnetic surface angular velocity Ω_B/Ω_H',
 '设置文件已损坏且无法备份：': 'The settings file is corrupted and cannot be backed up:',
 '预热帧数无效：不能为负数。': 'Invalid warm-up frame number: cannot be negative.',
 ' 个已完成的前置分析（最新：': 'completed pre-analysis (latest:',
 '无法调用系统进程树终止工具：': 'Unable to call system process tree termination tool:',
 '通量估计通常使用较低分辨率。': 'Flux estimates typically use lower resolution.',
 '内部错误：尝试写入未接入字段 ': 'Internal error: Attempt to write to unconnected field',
 '正在后台检查已完成的前置分析…': 'Checking completed pre-analysis in the background...',
 '请选择有效的插值误差输入目录。': 'Please select a valid interpolation error input directory.',
 '射线追迹允许的最大累计仿射长度。': 'The maximum cumulative affine length allowed for ray tracing.',
 '无法读取通量定标程序的默认配置：': 'Unable to read the default configuration of the flux scaling program:',
 '作业中的 paths 必须是对象。': 'paths in the job must be objects.',
 '快光匹配：请选择一个完整慢光结果。': 'Fast light match: Please select a complete slow light result.',
 '图像横纵坐标均显示 [-L, L]。': 'The horizontal and vertical coordinates of the image both display [-L, L].',
 '请至少输入一个 EVPA 对比时刻。': 'Please enter at least one EVPA comparison moment.',
 '图像边长无效（camera.npix=': 'The image side length is invalid (camera.npix=',
 '数据目录不存在或不可访问：请重新选择。': 'The data directory does not exist or is inaccessible: please select '
                        'again.',
 '绕黑洞自旋轴的方位角，界面以弧度输入。': "Azimuth angle around the black hole's spin axis, entered in radians on "
                        'the interface.',
 '通量定标默认配置不可用，无法生成作业。': 'The default configuration for flux scaling is not available and the job '
                        'cannot be generated.',
 'XZ 图中标记喷流边界的磁化率等值线值。': 'Magnetic susceptibility contour values marking jet boundaries in XZ '
                         'plots.',
 '起始帧，包含该帧；所选数据文件必须存在。': 'Starting frame, containing this frame; the selected data file must '
                         'exist.',
 '结果根目录尚未设置；运行计算后会自动填充。': 'The results root has not been set yet; it will be populated '
                          'automatically after running the calculation.',
 '。请用慢光相同参数和输入数据重跑快光后刷新。': '. Please rerun fast light with the same parameters and input data of '
                           'slow light and refresh.',
 '所选慢光结果没有共同的模型签名匹配快光结果。': 'The selected slow-light results do not have a common model signature '
                           'that matches the fast-light results.',
 '超出后丢弃最旧行；完整日志始终写入作业目录。': 'The oldest rows are discarded after exceeding; the full log is always '
                           'written to the job directory.',
 'GRMHD 吸积率归一化，必须与输入数据一致。': 'GRMHD accretion rate normalization, must be consistent with the input '
                            'data.',
 '当前有任务正在运行，完成或取消后才能清空记录。': 'There is currently a task running, and the record can only be cleared '
                            'after it is completed or canceled.',
 '电子数密度低于该阈值时，局域辐射转移系数置零。': 'When the electron number density is below this threshold, the local '
                            'radiative transfer coefficient is set to zero.',
 '支持普通整数和科学计数法；表达式结果必须为整数。': 'Normal integers and scientific notation are supported; the '
                             'expression result must be an integer.',
 '径向分布对角向积分；极角分布在指定径向壳层内积分。': 'The radial distribution is integrated over the angular direction; '
                              'the polar distribution is integrated within the specified radial '
                              'shell.',
 '<i>R</i>–β 电子温度模型的低磁化区温度比。': '<i>R</i>–β Low magnetization region temperature ratio for the '
                               'electron temperature model.',
 '单独运行慢光前置分析，不改变当前选中的正式计算任务。': 'Run slow-light pre-analysis alone without changing the currently '
                               'selected formal calculation task.',
 '观测频率；界面按 GHz 输入，作业内部换算为 Hz。': 'Observation frequency; input in GHz on the interface and '
                                'converted to Hz internally in the job.',
 '前置分析、慢光成像和区域误差共用；修改后会改变分析签名。': 'Pre-analysis, slow-light imaging and regional error are shared; '
                                 'modification will change the analysis signature.',
 '当前已有任务正在运行。请等待完成或先取消，再启动新任务。': 'There are currently tasks running. Please wait for completion or '
                                 'cancel before starting a new task.',
 '自动在数据目录及其父目录寻找唯一 grid_mks.in': 'Automatically look for the unique grid_mks.in in the data '
                                 'directory and its parent directory',
 '快光默认处理全部输入帧；也可填写连续帧范围用于小规模试算。': 'QuickLight processes all input frames by default; you can also '
                                  'fill in a continuous frame range for small-scale trial '
                                  'calculations.',
 '每次重复都会重新执行被计时的帧流程；网格和光线几何继续复用。': 'Each iteration re-executes the timed frame flow; mesh and ray '
                                   'geometry continue to be reused.',
 '辐射源区域的外边界半径；射线越过该半径并向外传播时终止追迹。': 'The outer boundary radius of the radiation source region; the '
                                   'trace terminates when the ray crosses this radius and '
                                   'propagates outward.',
 '没有可用于视频的 EVPA PNG；请同时勾选逐帧 EVPA。': 'There are no EVPA PNGs available for video; please also check '
                                    'frame-by-frame EVPA.',
 '结果根目录为空：请在“数据与模型”页的“网格与结果路径”中设置。': 'The result root directory is empty: please set it in "Grid '
                                     'and Result Path" on the "Data and Model" page.',
 '视频只读取已经生成的 PNG 序列；请先在“分布图”生成相应图件。': 'The video only reads the generated PNG sequence; please '
                                      'generate the corresponding image in "Distribution Map" '
                                      'first.',
 '结束输出帧，包含该帧；范围外必要 GRMHD 帧仍用于时间插值缓存。': 'End output frame, inclusive; necessary GRMHD frames '
                                       'outside the range are still used for temporal '
                                       'interpolation buffering.',
 'last_paths 必须只包含 data、grid、output 字符串。': 'last_paths must contain only data, grid, and output '
                                           'strings.',
 '发现多个 grid_mks.in 候选，请通过“网格与结果路径”明确选择一个。': 'Multiple grid_mks.in candidates found, please select '
                                            'one explicitly via "Grid & Result Path".',
 '平面选样的角向半宽；XZ 使用方位角到截面的偏差，XY 使用极角到赤道面的偏差。': 'The angular half-width of the plane sample; XZ uses '
                                             'the deviation from the azimuth angle to the cross '
                                             'section, and XY uses the deviation from the polar '
                                             'angle to the equatorial plane.',
 '性能图只适用于单个 Benchmark 结果；控制变量扫描需要多选至少两个完整慢光结果。': 'Performance graphs are only available for a '
                                                 'single Benchmark result; control variable sweeps '
                                                 'require a multi-selection of at least two full '
                                                 'slow-light results.',
 ' M☉/年 写入“正式计算”页的 Ṁ。建议值只是首猜：修改 Ṁ 后请重新运行 Flux 验证。': 'M☉/year Write Ṁ on the Formal Calculation '
                                                    'page. Suggested values are just first '
                                                    'guesses: please re-run Flux validation after '
                                                    'modifying Ṁ.',
 '确定取消当前任务吗？\n程序会先请求内部计算程序在当前帧边界安全停止；已写出的部分结果不会标记为完整。': 'Are you sure you want to cancel the '
                                                        'current task?\n'
                                                        'The program will first request a safe '
                                                        'stop of the internal calculation process '
                                                        'at the current frame boundary; partial '
                                                        'results that have been written out will '
                                                        'not be marked as complete.',
 'MKSBHAC 网格参数 h_s 直接读取 grid_mks.in 的 hslope，不在界面重复设置。': 'MKSBHAC grid parameter h_s directly '
                                                         'reads the hslope of grid_mks.in and does '
                                                         'not set it repeatedly in the interface.',
 '① 数据与辐射模型准备\u3000→\u3000② Flux 定标\u3000→\u3000③ 慢光前置分析\u3000→\u3000④ 正式快光/慢光计算\u3000→\u3000⑤ 结果后处理': '① '
                                                                                                       'Data '
                                                                                                       'and '
                                                                                                       'radiation '
                                                                                                       'model '
                                                                                                       'preparation '
                                                                                                       '→ '
                                                                                                       '② '
                                                                                                       'Flux '
                                                                                                       'calibration '
                                                                                                       '→ '
                                                                                                       '③ '
                                                                                                       'Slow '
                                                                                                       'light '
                                                                                                       'pre-analysis '
                                                                                                       '→ '
                                                                                                       '④ '
                                                                                                       'Formal '
                                                                                                       'fast '
                                                                                                       'light/slow '
                                                                                                       'light '
                                                                                                       'calculation '
                                                                                                       '→ '
                                                                                                       '⑤ '
                                                                                                       'Result '
                                                                                                       'post-processing',
 '视频采用 1920×1080 标准画布，原图等比例缩放并留边，不会裁剪或拉伸；若尚无 PNG，请同时勾选逐帧 EVPA。': 'The video uses a 1920×1080 '
                                                                 'standard canvas. The original '
                                                                 'image is scaled proportionally '
                                                                 'and leaves edges, and will not '
                                                                 'be cropped or stretched. If '
                                                                 'there is no PNG, please also '
                                                                 'check frame-by-frame EVPA.',
 '实际选择满足 n<sub>0</sub> + k Δn ≤ n<sub>1</sub> 的帧；未对齐的 n<sub>1</sub> 不额外加入。': 'Frames satisfying '
                                                                             'n<sub>0</sub> + k Δn '
                                                                             '≤ n<sub>1</sub> are '
                                                                             'actually selected; '
                                                                             'unaligned '
                                                                             'n<sub>1</sub> are '
                                                                             'not added '
                                                                             'additionally.',
 ';\n    font-size: 11px;\n}\n\n/* ---------- 进度与表格 ---------- */\nQProgressBar {\n    background: ': ';\n'
                                                                                                      '    '
                                                                                                      'font-size: '
                                                                                                      '11px;\n'
                                                                                                      '}\n'
                                                                                                      '\n'
                                                                                                      '/* '
                                                                                                      '---------- '
                                                                                                      'Progress '
                                                                                                      'and '
                                                                                                      'table '
                                                                                                      '---------- '
                                                                                                      '*/\n'
                                                                                                      'QProgressBar '
                                                                                                      '{\n'
                                                                                                      '    '
                                                                                                      'background:',
 ';\n}\n\n/* ---------- 滚动条 ---------- */\nQScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }\nQScrollBar::handle:vertical {\n    background: ': ';\n'
                                                                                                                                                                         '}\n'
                                                                                                                                                                         '\n'
                                                                                                                                                                         '/* '
                                                                                                                                                                         '---------- '
                                                                                                                                                                         'scroll '
                                                                                                                                                                         'bar '
                                                                                                                                                                         '---------- '
                                                                                                                                                                         '*/\n'
                                                                                                                                                                         'QScrollBar:vertical '
                                                                                                                                                                         '{ '
                                                                                                                                                                         'background: '
                                                                                                                                                                         'transparent; '
                                                                                                                                                                         'width: '
                                                                                                                                                                         '10px; '
                                                                                                                                                                         'margin: '
                                                                                                                                                                         '2px; '
                                                                                                                                                                         '}\n'
                                                                                                                                                                         'QScrollBar::handle:vertical '
                                                                                                                                                                         '{\n'
                                                                                                                                                                         '    '
                                                                                                                                                                         'background:'}

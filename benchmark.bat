@echo off
setlocal enabledelayedexpansion

echo ========================================
echo   LUMINA BENCHMARK SUITE
echo ========================================
echo.

set RESULTS_FILE=benchmark_results.txt
echo Lumina Benchmark Results > %RESULTS_FILE%
echo ========================== >> %RESULTS_FILE%
echo. >> %RESULTS_FILE%

echo [1/6] Compiling bench_simple...
powershell -command "$t = Measure-Command { python lumina\main.py build Examples\bench_simple.lm }; $t.TotalMilliseconds" >> %RESULTS_FILE% 2>&1

echo [2/6] Compiling bench_noise...
powershell -command "$t = Measure-Command { python lumina\main.py build Examples\bench_noise.lm }; $t.TotalMilliseconds" >> %RESULTS_FILE% 2>&1

echo [3/6] Compiling bench_fractal...
powershell -command "$t = Measure-Command { python lumina\main.py build Examples\bench_fractal.lm }; $t.TotalMilliseconds" >> %RESULTS_FILE% 2>&1

echo.
echo [4/6] Running bench_simple...
powershell -command "$t = Measure-Command { .\bench_simple.exe }; $t.TotalMilliseconds" >> %RESULTS_FILE% 2>&1

echo [5/6] Running bench_noise...
powershell -command "$t = Measure-Command { .\bench_noise.exe }; $t.TotalMilliseconds" >> %RESULTS_FILE% 2>&1

echo [6/6] Running bench_fractal...
powershell -command "$t = Measure-Command { .\bench_fractal.exe }; $t.TotalMilliseconds" >> %RESULTS_FILE% 2>&1

echo.
echo Getting file sizes...
echo. >> %RESULTS_FILE%
echo File Sizes: >> %RESULTS_FILE%
dir bench_*.exe >> %RESULTS_FILE% 2>&1

echo. >> %RESULTS_FILE%
echo C File Lines: >> %RESULTS_FILE%
find /c /v "" bench_simple.c >> %RESULTS_FILE% 2>&1
find /c /v "" bench_noise.c >> %RESULTS_FILE% 2>&1
find /c /v "" bench_fractal.c >> %RESULTS_FILE% 2>&1

echo.
echo ========================================
echo ✅ Benchmark complete!
echo Results saved to: %RESULTS_FILE%
echo ========================================
echo.
type %RESULTS_FILE%
pause
@echo off

echo 开始运行基金预测系统...

REM 1. 获取基金数据
echo 1. 获取基金数据...
python scripts\fetch_data.py
if %ERRORLEVEL% NEQ 0 (
    echo 获取基金数据失败，请检查网络连接或API配置。
    pause
    exit /b 1
)

REM 2. 训练模型
echo 2. 训练模型...
python scripts\train_model.py
if %ERRORLEVEL% NEQ 0 (
    echo 训练模型失败，请检查数据格式或模型参数。
    pause
    exit /b 1
)

REM 3. 生成预测
echo 3. 生成预测...
python scripts\predict.py
if %ERRORLEVEL% NEQ 0 (
    echo 生成预测失败，请检查模型文件或API连接。
    pause
    exit /b 1
)

REM 4. 显示结果
echo 4. 预测完成！
echo 预测结果已保存到 data\predictions\all_predictions.json

pause
# src/train_model.py
import torch
import pandas as pd
import argparse
import os
import sys
from model import FundTradingModel
from torch.utils.data import DataLoader, TensorDataset

def train(args):
    # 确保文件存在
    if not os.path.exists(args.data):
        print(f"Error: Data file {args.data} does not exist!")
        sys.exit(1)
    
    # 加载预处理数据
    data = pd.read_parquet(args.data)
    features = data.drop(columns=['signal']).values
    targets = data['signal'].values
    
    # 创建序列数据
    sequences = []
    labels = []
    for i in range(len(features) - args.seq_len):
        sequences.append(features[i:i+args.seq_len])
        labels.append(targets[i+args.seq_len])
    
    # 数据集划分
    train_size = int(len(sequences) * 0.8)
    train_dataset = TensorDataset(
        torch.FloatTensor(sequences[:train_size]),
        torch.LongTensor(labels[:train_size])
    )
    
    # 初始化模型
    model = FundTradingModel(
        input_size=features.shape[1],
        hidden_size=64,
        num_layers=2,
        output_size=3
    )
    
    # 训练循环
    train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    criterion = torch.nn.CrossEntropyLoss()
    
    for epoch in range(args.epochs):
        for batch_x, batch_y in train_loader:
            optimizer.zero_grad()
            outputs = model(batch_x)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
    
    # 确保模型目录存在
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    # 保存模型
    torch.save(model.state_dict(), args.output)
    print(f"Model saved to {args.output}")
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--epochs', type=int, default=50)
    parser.add_argument('--seq_len', type=int, default=30)
    args = parser.parse_args()
    
    train(args)

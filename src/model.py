import torch
import torch.nn as nn

class FundTradingModel(nn.Module):
    def __init__(self, input_size, hidden_size, num_layers, output_size):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size, 
            hidden_size, 
            num_layers, 
            batch_first=True,
            dropout=0.2
        )
        self.attention = nn.Sequential(
            nn.Linear(hidden_size, 32),
            nn.Tanh(),
            nn.Linear(32, 1),
            nn.Softmax(dim=1)
        )
        self.fc = nn.Linear(hidden_size, output_size)
        
    def forward(self, x):
        # LSTM层
        out, _ = self.lstm(x)
        
        # 注意力机制
        attn_weights = self.attention(out)
        context = torch.sum(attn_weights * out, dim=1)
        
        # 分类层
        return self.fc(context)

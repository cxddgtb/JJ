# src/test_pytorch.py
import torch

def test_pytorch():
    print(f"PyTorch version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    print(f"Device: {torch.device('cuda' if torch.cuda.is_available() else 'cpu')}")
    
    # 创建一个简单的张量
    x = torch.rand(2, 3)
    print(f"Random tensor:\n{x}")
    
    print("PyTorch installation test successful!")

if __name__ == "__main__":
    test_pytorch()

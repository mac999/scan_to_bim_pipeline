import torch

flag = torch.cuda.is_available()
if flag:
	print(torch.cuda.device_count())
	print(torch.cuda.current_device())
	print(torch.cuda.device(0))
	print(torch.cuda.get_device_name(0))
 
 
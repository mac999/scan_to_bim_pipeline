import os, json, glob, argparse, fnmatch, traceback, threading, csv
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from scipy import stats

def get_factor(name, tag, end_tag):
	tokens = name.split('_')

	factor = 0.0
	for i in range(len(tokens)):
		token = tokens[i]
		if token[0] == tag:
			factor = token[1:]
			if len(end_tag):
				dot_index = token.rindex(end_tag)
				factor = token[1:dot_index]
			break
	return float(factor)

def save_image(fname, df, key1, key2, desc):
	value1 = df[key1].tolist()
	value2 = df[key2].tolist()

	slope, intercept, r_value, p_value, std_err = stats.linregress(value1, value2)
	def regression_line(values):
		return [x * slope + intercept for x in values]
	regression_line_values = regression_line(value1)

	plt.clf()
	plt.scatter(np.asarray(value1), np.asarray(value2), c='g', s=20, alpha=0.9)
	plt.plot(value1, regression_line_values, label='Regression Line', color='blue')

	x_min, x_max = plt.xlim()
	y_min, y_max = plt.ylim()
	mid_x = (x_max + x_min) / 2
	top_y = y_max - 0.2
	plt.text(mid_x, top_y, f'R = {r_value:.2f}', ha='center', va='top')

	output = fname.replace('#', label + '_chart_' + str(index))
	output = output.replace('csv', 'png')

	# plt.gca().set_aspect("equal")
	log = f"{desc}"
	plt.title(log)
	plt.xlabel(key1)
	plt.ylabel(key2)
	plt.savefig(fname)

def main():
	parser = argparse.ArgumentParser(description='seg to geo ml')
	parser.add_argument('--input', type=str, default='./seg_to_geo_ml/log20231204_1/pcd_to_geo*.csv', help='input CSV file')
	parser.add_argument('--output', type=str, default='./seg_to_geo_ml/log20231204_1/merge_#.csv', help='output CSV file')
	args = parser.parse_args()

	if os.path.exists(args.output):
		os.remove(args.output)

	merged_data = pd.DataFrame()
	input_files = glob.glob(args.input)
	for index, fname in enumerate(input_files):
		df = pd.read_csv(fname) # , header=None, skiprows=1)

		df['alpha'] = get_factor(fname, 'a', '')
		df['smooth'] = get_factor(fname, 's', '.')
		merged_data = pd.concat([merged_data, df], ignore_index=True)

	output = args.output.replace('#', 'all')
	merged_data.to_csv(output, index=False)

	merged_data = pd.DataFrame()
	input_files = glob.glob(args.input)
	for index, fname in enumerate(input_files):
		df = pd.read_csv(fname) # , header=None, skiprows=1)

		alpha = get_factor(fname, 'a', '')
		smooth = get_factor(fname, 's', '.')
		df['alpha'] = alpha 
		df['smooth'] = smooth
		label = df['class']

		df_no_duplicates = df.drop_duplicates(subset=['outline_size'])
		desc = f'a={alpha:.2f}, s={smooth:.3f}'
		save_image(args.output, df_no_duplicates, 'outline_size', 'outline_area_accuracy', desc)

		merged_data = pd.concat([merged_data, df_no_duplicates], ignore_index=True)
	output = args.output.replace('#', 'list')
	merged_data.to_csv(output, index=False)

	print(f'Merged data saved to: {args.output}')

if __name__ == '__main__':
	main()
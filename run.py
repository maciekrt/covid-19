import subprocess
import argparse
import sys
import sentry_sdk
import nbformat 
from datetime import datetime
from datetime import date
from nbconvert.preprocessors import ExecutePreprocessor

parser = argparse.ArgumentParser()
parser.add_argument("--force", action="store_true")
parser.add_argument("--sentry-url")
args = parser.parse_args()
flagForce = args.force
sentryUrl = args.sentry_url

# sentry init
sentry_sdk.init(dsn=sentryUrl)

# Execution function
run_path = "./"
data_path = "Rt Data Preparation.ipynb"
model_path = "Rainier.ipynb"

def execute(path,kernel):
	with open(f"{run_path}{path}") as f:
		nb = nbformat.read(f, as_version=4)
		ep = ExecutePreprocessor(timeout=3600, kernel_name=kernel)
		try:
			out = ep.preprocess(nb, {'metadata': {'path': run_path}})
		except CellExecutionError:
			msg = 'Error executing the notebook "%s".\n\n' % path
			msg += 'See notebook "%s" for the traceback.' %  f"executed{path}"
			print(msg)
			raise
		finally:
			with open(f"{run_path}executed_{path}", 'w', encoding='utf-8') as f:
				nbformat.write(nb, f)
			

try:
	commandLatest = """git log --author="cronjob" -1 --date=short --pretty=format:%cd"""
	cp = subprocess.run(commandLatest, shell=True, check=True, text=True, capture_output=True)
	dateOfCommit = date.fromisoformat(cp.stdout)
	if not flagForce:
		print("Last data push on", dateOfCommit)
	today = date.today()
	if dateOfCommit == today and not flagForce:
		print("Already pushed today!")
		quit()

	print("Execution on", today)
	if flagForce:
		print("Forcing!")

	now = datetime.now()

	# Running data preparation and model notebooks
	execute(data_path,'python3')
	execute(model_path,'rainier')

	# Pushing everything to git repository
	commandConfig = """git config user.name "cronjob" && git config user.email hello@rteu.live"""
	commandExecution = f"""git commit -a -m"Updating rt-rainier.csv on {now}" && git push"""
	subprocess.run(commandConfig, shell=True, check=True)
	subprocess.run(commandExecution, shell=True, check=True)
except Exception as e:
	sentry_sdk.capture_exception(e)
	raise e

#
# Get version as defined by GIT
#
import subprocess
import sys
import os

version = os.getenv('GITHUB_REF_NAME')
if version is None:
  cwd = '.'
  rc = subprocess.run(['git','describe'],
                      capture_output=True,
                      text=True,
                      cwd=cwd)
  if rc.returncode != 0:
    sys.stderr.write('RUN ERROR: {}\n'.format(str(rc)))
    sys.exit(1)
  version = rc.stdout.strip()

if len(sys.argv) > 1 and sys.argv[1] == '--next':
  next_dev = '-next(DEV)'
  sys.argv.pop(1)
else:
  next_dev = ''


outp = 'VERSION = \'{}{}\'\n'.format(version, next_dev)
if len(sys.argv) == 2:
  with open(sys.argv[1],'w') as fp:
    fp.write(outp)
else:
  print(outp)

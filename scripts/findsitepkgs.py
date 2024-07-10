
import site,os

for i in site.getsitepackages():
  if os.path.basename(i) == 'site-packages':
    print("SET sitedir={}".format(i))

  

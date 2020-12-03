#Usage From ENM Scripting VM: python export_IBase.py
#For CMGD. --tracy.rao
#20191112: add codes to try to get hostname from /etc/hosts
#20200102: add logic to ignor "Error 8013 : Search criteria did not match any nodes" if ENM contains only one type(G1/G2) of Enodebs
#20200109: improve exit logic
#20200218: adjust CLI with option --syncstate sync --prettyformat true
#20200228: add rename ENM host name function. In future, if any of the ENM scheme change, edit it in the renameENM() function accordingly.
#20200305: change --syncstate to all
#For CMCQ. --Weijian.Li
#20200902: Change site info from CMGD to CMCQ


import enmscripting
import os,socket
import time,sys,shutil
import datetime,zipfile
timeout = 1200

#using # between to string as follow
def renameENM(hostname):
	if hostname == 'scp-1':
		return 'sxcultems_enm#SX#10.100.69.4'
try:
	session = enmscripting.open() #<enm_url> <username> <password>
	hostname=socket.gethostname()[:5]  #eg. scp-2-scripting
	#try to get the readable hostname of the physical machine
	with open('/etc/hosts','r') as f:
		for l in f:
			if 'enm' in l:
				datas=l.split('.')
				for item in datas:
					if 'enm' in item:
						if len(item)>3:
							hostname=item
							break
				break
	basePath=sys.path[0]
	homedir=os.path.expanduser('~')
	userDefinedfilter=[os.path.join(basePath,'G1_iBase_Filter.txt'),os.path.join(basePath,'G2_iBase_Filter.txt')]
	#userDefinedfilter = [ os.path.join(basePath, 'G2_iBase_Filter.txt')]
	ibaseOutputDir=homedir+'/ibaseCollect/'

	if not os.path.exists(ibaseOutputDir):
		os.mkdir(ibaseOutputDir)
	else:
		print('Removing the old IB_* files under '+ibaseOutputDir+' ...')
		os.system('rm '+ibaseOutputDir+'IB_*'+'.zip')

	terminal = session.terminal()
	for filter in userDefinedfilter:
		if 'G1' in filter:
			jobname = 'IB_CUShanXi_eNodeB_G1_'+datetime.datetime.now().strftime('%Y%m%d_%H%M')+'-'+hostname
			command='cmedit export -f file:{ff}  --netype ERBS --filetype 3GPP --jobname {jn} --syncstate all --prettyformat true'.format(ff=(os.path.basename(filter)),jn=jobname)
			print(command)
		if 'G2' in filter:
			jobname = 'IB_CUShanXi_eNodeB_G2_gNodeB_'+datetime.datetime.now().strftime('%Y%m%d_%H%M')+'-'+hostname
			command = 'cmedit export -f file:{ff} --netype RadioNode --filetype 3GPP --jobname {jn}  --syncstate all --prettyformat true'.format(ff=(os.path.basename(filter)),jn=jobname)
			print(command)
		with open(filter, "rb") as f:
			response = terminal.execute(command, f) # response = terminal.execute(command) #if no filter file
		print("read: {f}".format(f=filter))
		print(response)
		if 'Error 8013 : Search criteria did not match any nodes' in response.get_output():
			continue
		else:
			if 'Error' in response.get_output():
				for line in response.get_output():
					print ('[CheckExportCLI] '+line)
				enmscripting.close(session)
				sys.exit(0)
			else:
				while True:
					command = 'cmedit export --status --jobname ' + jobname
					response = terminal.execute(command)
					result = response.get_output()
					try:
						if 'COMPLETED' in result[2]:
							for line in result:
								print ('[JobCOMPLETED] '+line)
							command = 'cmedit export --download --jobname ' + jobname
							response = terminal.execute(command)
							if response.has_files():
								for enm_file in response.files():
									print('Downloading exported file...')
									enm_file.download()
								break
						else:
							for line in result:
								print ('[CheckJobStatus] '+line)
							for line in result:
								if 'FAILED' in result[2]:
									enmscripting.close(session)
									sys.exit()
								if 'Error' in line:
									enmscripting.close(session)
									sys.exit(0)
							time.sleep(8)
					except IndexError:
						pass
					pass
			print('Renaming exported file by adjusting ENM suffix and moving it to '+ibaseOutputDir+' ...')
			hostname_new=renameENM(hostname)
			outputFile=jobname+'.zip'
			outputXML_File = outputFile.replace('zip', 'xml')
			outputXML_File_new = outputXML_File.replace(hostname,hostname_new)
			outputFile_new = outputXML_File_new.replace('xml', 'zip')
			zf = zipfile.ZipFile(outputFile)
			try:
				zf.extractall()
			except Exception as e:
				print(e)
			zf.close()
			os.rename(outputXML_File, outputXML_File_new)
			# compress file
			zf = zipfile.ZipFile(outputFile_new, 'w')
			zf.write(outputXML_File_new, os.path.basename(outputXML_File_new), zipfile.ZIP_DEFLATED)
			zf.close()
			os.remove(outputXML_File_new)
			os.remove(outputFile)
			shutil.move(outputFile_new,ibaseOutputDir+outputFile_new)
			#print('Removing the export job...')
			#response=terminal.execute('cmedit export --remove --jobname ' + jobname)
			#print(response)
	enmscripting.close(session)
	print('Finished. Please check IBase files in '+ibaseOutputDir)
except KeyboardInterrupt as e:
	print(e)
	enmscripting.close(session)
	sys.exit(0)

import tarfile
import os


def create_tar_archive(output_file, needed_files):
	# Get the directory containing the script as the build context
	script_directory = os.path.dirname(os.path.abspath(__file__))

	# Create a tar archive
	with tarfile.open(output_file, "w") as tar:
		# Add all files in the build context to the archive
		for root, dirs, files in os.walk(script_directory):
			for file in files:
				for needed_file in needed_files:
					if file == needed_file:
						file_path = os.path.join(root, file)
						tar.add(file_path,
						        arcname=os.path.relpath(
						            file_path, script_directory))

	print(f"Tar archive created: {output_file}")


# Provide the name of the output tar archive
output_filename = "skinbaron.tar"

needed_files = ["Dockerfile", "requirements.txt", "skinbaron.py"]

# Create the tar archive
create_tar_archive(output_filename, needed_files)

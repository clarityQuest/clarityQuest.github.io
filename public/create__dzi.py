import pyvips

# Replace with your actual filename if different
input_file = "C:\\Users\\sknue\\OneDrive\\Desktop\\Proj\\tabula-peutingeriana\\public\\Tabula_Peutingeriana_-_Miller.jpg"
output_basename = "C:\\Users\\sknue\\OneDrive\\Desktop\\Proj\\tabula-peutingeriana\\public\\Tabula_Peutingeriana_-_Miller"

image = pyvips.Image.new_from_file(input_file, access="sequential")
image.dzsave(output_basename)
print("DZI created successfully!")
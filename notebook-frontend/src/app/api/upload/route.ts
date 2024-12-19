import { NextRequest, NextResponse } from "next/server";
import { writeFile, mkdir } from "fs/promises";
import { join } from "path";

export async function POST(request: NextRequest) {
  try {
    // Ensure the upload directory exists
    const uploadDir = join(process.cwd().split('/').slice(0, -1).join('/'), 'notebook-backend', 'public', 'uploads');
    console.log("uploadDir", uploadDir)
    try {
      await mkdir(uploadDir, { recursive: true });
    } catch (err) {
      // Directory might already exist, that's ok
      console.error("Error creating upload directory", err)
    }

    // Get the form data from the request
    const formData = await request.formData();
    const file = formData.get('file') as File;

    if (!file) {
      return NextResponse.json(
        { error: 'No file received' },
        { status: 400 }
      );
    }

    // Validate file type
    const allowedTypes = ['text/csv', 'application/json'];
    if (!allowedTypes.includes(file.type)) {
      return NextResponse.json(
        { error: 'Invalid file type. Only CSV and JSON files are allowed.' },
        { status: 400 }
      );
    }

    // Create a unique filename
    const timestamp = Date.now();
    const originalName = file.name;
    const extension = originalName.split('.').pop();
    const filename = `${timestamp}-${originalName}`;
    const filepath = join(uploadDir, filename);

    console.log("extension", extension)

    // Convert the file to buffer
    const bytes = await file.arrayBuffer();
    const buffer = Buffer.from(bytes);

    // Write the file to the filesystem
    await writeFile(filepath, buffer);
    
    return NextResponse.json({
      message: 'File uploaded successfully',
      filePath: '/public/uploads/' + filename
    });

  } catch (error) {
    console.error('Error in file upload:', error);
    return NextResponse.json(
      { error: 'Error uploading file' },
      { status: 500 }
    );
  }
}

// Configure the API route to handle larger files
export const config = {
  api: {
    bodyParser: false, // Disable the default body parser
  },
};
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.middleware.cors import CORSMiddleware
import io
from app.converter import parse_pdf, generate_ofx

app = FastAPI(title="PDF to OFX Converter")

# Enable CORS for local network access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/analyze")
async def analyze_pdf_endpoint(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    try:
        content = await file.read()
        file_obj = io.BytesIO(content)
        
        # We only need extracted info here
        _, account_info = parse_pdf(file_obj)
        
        return JSONResponse(content=account_info)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/convert")
async def convert_pdf(
    file: UploadFile = File(...),
    bank_id: str = Form(None),
    branch_id: str = Form(None),
    acct_id: str = Form(None)
):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    try:
        content = await file.read()
        file_obj = io.BytesIO(content)
        
        transactions, extracted_info = parse_pdf(file_obj)
        
        # Override with user provided info if available
        account_info = extracted_info.copy()
        if bank_id: account_info['bank_id'] = bank_id
        if branch_id: account_info['branch_id'] = branch_id
        if acct_id: account_info['acct_id'] = acct_id
        
        if not transactions:
            raise HTTPException(status_code=400, detail="No transactions found in PDF")
            
        ofx_content = generate_ofx(transactions, account_info)
        
        return StreamingResponse(
            io.BytesIO(ofx_content.encode('latin-1', errors='replace')),
            media_type="application/x-ofx",
            headers={"Content-Disposition": f"attachment; filename={file.filename.replace('.pdf', '.ofx')}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

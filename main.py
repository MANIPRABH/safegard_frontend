from fastapi import FastAPI, UploadFile, File, Form
from pydantic import BaseModel
from fastapi.responses import JSONResponse
import os
from datetime import datetime
import mysql.connector

app = FastAPI()

# MySQL Connection
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root",
    database="emergency_app"
)

def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="emergency_app"
    )

cursor = db.cursor(dictionary=True)


# Pydantic Models
class RegisterUser(BaseModel):
    fullname: str
    email: str
    password: str
    phone_number: str
    address: str
    gender: str


class LoginUser(BaseModel):
    email: str
    password: str

class EmergencyContact(BaseModel):
    user_id: int
    contact_name: str
    contact_number: str

class MedicalInfo(BaseModel):
    user_id: int
    blood_group: str
    allergies: str
    medical_conditions: str
    medications: str

from pydantic import BaseModel

class FamilyMember(BaseModel):
    id:int
    member_name:str
    relation:str
    phone:str
    latitude:float
    longitude:float
    battery:int
    location_name:str

@app.post("/login")
def login_user(user: LoginUser):

    query = "SELECT * FROM users WHERE email=%s AND password=%s"
    cursor.execute(query,(user.email,user.password))

    result = cursor.fetchone()

    if result:
        return {
            "status": "success",
            "message": "Login successful",
            "id": result["id"],
            "fullname": result["fullname"],
            "email": result["email"]
        }
    else:
        return {
            "status": "error",
            "message": "Invalid email or password"
        }


@app.post("/register")
def register_user(user: RegisterUser):

    cursor.execute("SELECT * FROM users WHERE email=%s",(user.email,))
    existing = cursor.fetchone()

    if existing:
        return {
            "status": "error",
            "message": "Email already registered"
        }

    query = """
    INSERT INTO users(fullname,email,password,phone_number,address,gender)
    VALUES (%s,%s,%s,%s,%s,%s)
    """

    cursor.execute(query,(
        user.fullname,
        user.email,
        user.password,
        user.phone_number,
        user.address,
        user.gender
    ))

    db.commit()

    return {
        "status": "success",
        "message": "User registered successfully"
    }

@app.post("/save-emergency-contact")
def save_emergency_contact(contact: EmergencyContact):

    query = """
    INSERT INTO emergency_contacts (user_id, contact_name, contact_number)
    VALUES (%s,%s,%s)
    """

    cursor.execute(query,(
        contact.user_id,
        contact.contact_name,
        contact.contact_number
    ))

    db.commit()

    return {
        "status":"success",
        "message":"Emergency contact saved successfully"
    }

@app.post("/medical-info")
def save_medical_info(info: MedicalInfo):

    cursor.execute("SELECT * FROM medical_info WHERE user_id=%s",(info.user_id,))
    existing = cursor.fetchone()

    if existing:

        query = """
        UPDATE medical_info
        SET blood_group=%s,
            allergies=%s,
            medical_conditions=%s,
            medications=%s
        WHERE user_id=%s
        """

        cursor.execute(query,(
            info.blood_group,
            info.allergies,
            info.medical_conditions,
            info.medications,
            info.user_id
        ))

        db.commit()

        return {
            "status":"success",
            "message":"Medical info updated"
        }

    else:

        query = """
        INSERT INTO medical_info
        (user_id,blood_group,allergies,medical_conditions,medications)
        VALUES (%s,%s,%s,%s,%s)
        """

        cursor.execute(query,(
            info.user_id,
            info.blood_group,
            info.allergies,
            info.medical_conditions,
            info.medications
        ))

        db.commit()

        return {
            "status":"success",
            "message":"Medical info saved"
        }
    
@app.get("/medical-info/{user_id}")
def get_medical_info(user_id:int):

    cursor.execute("SELECT * FROM medical_info WHERE user_id=%s",(user_id,))
    data = cursor.fetchone()

    if data:
        return {
            "status":"success",
            "data":data
        }

    return {
        "status":"empty",
        "message":"No medical info found"
    }

@app.get("/family/{guardian_id}")
def get_family_members(guardian_id: int):

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            fm.id,
            u.fullname AS member_name,
            fm.relation,
            u.phone_number AS phone,
            0 AS latitude,
            0 AS longitude,
            70 AS battery,
            IFNULL(u.address, 'Unknown') AS location_name
        FROM family_memberss fm
        JOIN users u ON fm.member_id = u.id
        WHERE fm.guardian_id = %s
    """, (guardian_id,))

    rows = cursor.fetchall()

    members = []

    for r in rows:
        members.append({
            "id": r[0],
            "member_name": r[1],
            "relation": r[2],
            "phone": r[3],
            "latitude": float(r[4]),
            "longitude": float(r[5]),
            "battery": int(r[6]),
            "location_name": r[7]
        })

    cursor.close()
    conn.close()

    return {
        "status": "success",
        "members": members
    }

class GuardianRegister(BaseModel):
    name: str
    email: str
    phone: str
    password: str


@app.post("/guardian/register")
def register_guardian(data: GuardianRegister):

    cursor.execute("SELECT * FROM guardians WHERE email=%s", (data.email,))
    existing = cursor.fetchone()

    if existing:
        return {
            "status": "error",
            "message": "Email already registered"
        }

    cursor.execute("""
        INSERT INTO guardians (name,email,phone,password)
        VALUES (%s,%s,%s,%s)
    """,(data.name,data.email,data.phone,data.password))

    db.commit()

    return {
        "status":"success",
        "message":"Guardian registered successfully"
    }

class GuardianLogin(BaseModel):
    email: str
    password: str


@app.post("/guardian/login")
def login_guardian(data: GuardianLogin):

    cursor.execute("""
        SELECT * FROM guardians
        WHERE email=%s AND password=%s
    """,(data.email,data.password))

    user = cursor.fetchone()

    if user:

        return {
            "status":"success",
            "message":"Login successful",
            "guardian":{
                "id":user["id"],
                "name":user["name"],
                "email":user["email"],
                "phone":user["phone"]
            }
        }

    return {
        "status":"error",
        "message":"Invalid email or password"
    }

@app.get("/guardian/dashboard/{guardian_id}")
def get_dashboard(guardian_id:int):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
    SELECT 
        COALESCE(SUM(CASE WHEN alert_type='SAFE' THEN 1 ELSE 0 END),0) AS safe_count,
        COALESCE(SUM(CASE WHEN alert_type='OFFLINE' THEN 1 ELSE 0 END),0) AS offline_count,
        COALESCE(SUM(CASE WHEN alert_type='SOS' THEN 1 ELSE 0 END),0) AS alert_count
    FROM alerts 
    WHERE member_id IN (
        SELECT member_id FROM family_memberss WHERE guardian_id=%s
    )
""", (guardian_id,))

    stats = cursor.fetchone()

    cursor.execute("""
    SELECT u.fullname,u.phone_number,a.location, a.latitude,
    a.longitude
    FROM alerts a
    JOIN users u ON u.id=a.member_id
    WHERE a.alert_type='SOS'
    LIMIT 1
    """)

    active_alert = cursor.fetchall()

    cursor.execute("""
    SELECT u.id,u.fullname,u.phone_number
    FROM family_memberss f
    JOIN users u ON u.id=f.member_id
    WHERE f.guardian_id=%s
    """,(guardian_id,))

    users = cursor.fetchall()

    return {
        "status":"success",
        "stats":stats,
        "active_alerts":active_alert,
        "users":users
    }

@app.get("/guardian/family/{guardian_id}")
def get_family_members(guardian_id: int):

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            u.id AS user_id,
            u.fullname AS name,
            a.alert_type AS status,
            a.location,
            a.latitude,
            a.longitude,
            a.created_at
        FROM family_memberss f
        JOIN users u ON u.id = f.member_id

        LEFT JOIN alerts a ON a.id = (
            SELECT id 
            FROM alerts 
            WHERE member_id = u.id 
            AND member_type = 'user'
            ORDER BY created_at DESC
            LIMIT 1
        )

        WHERE f.guardian_id = %s
    """, (guardian_id,))

    members = cursor.fetchall()

    return {
        "status": "success",
        "members": members
    }

# class AddMemberRequest(BaseModel):
#     guardian_id:int
#     fullname:str
#     phone_number:str
#     relation:str

# @app.post("/guardian/add-member")
# def add_member(request: AddMemberRequest):
    cursor = db.cursor(dictionary=True)
    try:
        # check user by phone
        cursor.execute(
            "SELECT id FROM users WHERE phone_number=%s",
            (request.phone_number,)
        )
        user = cursor.fetchone()

        if not user:
            return {
                "status": "error",
                "message": "User not registered in app"
            }

        member_id = user["id"]

        # insert family relation
        cursor.execute("""
            INSERT INTO family_members
            (guardian_id, member_id, member_type, relation)
            VALUES (%s, %s, 'user', %s)
        """, (request.guardian_id, member_id, request.relation))

        # insert initial alert record for this member
        cursor.execute("""
            INSERT INTO alerts
            (member_id, member_type, alert_type)
            VALUES (%s, 'user', 'SAFE')
        """, (member_id,))

        db.commit()

        return {
            "status": "success",
            "message": "Family member added successfully"
        }
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        cursor.close()

@app.get("/guardian/protected-users/{guardian_id}")
def get_protected_users(guardian_id:int):

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            u.id as user_id,
            u.fullname as name,
            a.location
        FROM family_memberss f
        JOIN users u ON u.id = f.member_id
        JOIN alerts a ON a.id = (
            SELECT id
            FROM alerts
            WHERE member_id = u.id
            ORDER BY created_at DESC
            LIMIT 1
        )
        WHERE f.guardian_id=%s
        AND a.alert_type='SAFE'
    """,(guardian_id,))

    users = cursor.fetchall()

    return {
        "status":"success",
        "users":users
    }


class SOSRequest(BaseModel):
    user_id:int
    latitude:float
    longitude:float
    location:str



@app.post("/user/sos")
def send_sos(data: SOSRequest):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        UPDATE alerts
        SET location = %s,
            latitude = %s,
            longitude = %s,
            alert_type = 'SOS',
            member_type = 'user'
        WHERE member_id = %s
    """,(
        data.location,
        data.latitude,
        data.longitude,
        data.user_id
    ))
    cursor.execute("""
            SELECT guardian_id 
            FROM family_memberss
            WHERE member_id = %s
        """, (data.user_id,))

    guardians = cursor.fetchall()
    for g in guardians:
        cursor.execute("""
            INSERT INTO notifications
            (sender_id, receiver_id, message, type, latitude, longitude)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            data.user_id,
            g["guardian_id"],
            "SOS Alert! Immediate attention needed.",
            "SOS",
            data.latitude,
            data.longitude
        ))

    db.commit()

    return {
        "status":"success",
        "message":"SOS Alert Updated"
    }

@app.get("/get_notifications/{guardian_id}")
def get_notifications(guardian_id: int):

    db = get_db()
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT * FROM notifications 
            WHERE receiver_id=%s 
            ORDER BY created_at DESC
        """, (guardian_id,))

        notifications = cursor.fetchall()

        # ✅ Convert datetime to string
        for n in notifications:
            if n.get("created_at"):
                n["created_at"] = n["created_at"].strftime("%Y-%m-%d %H:%M:%S")

        return {
            "status": "success",
            "notifications": notifications
        }

    finally:
        cursor.close()
        db.close()

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.post("/upload_document")
async def upload_document(
    user_id: int = Form(...),
    document_type: str = Form(...),
    file: UploadFile = File(...)
):
    try:
        # Create unique file name
        filename = f"{user_id}_{document_type}_{int(datetime.now().timestamp())}.jpg"
        file_path = os.path.join(UPLOAD_FOLDER, filename)

        # Save file
        with open(file_path, "wb") as f:
            f.write(await file.read())

        # Save to DB
        db = get_db()
        cursor = db.cursor()

        cursor.execute("""
            INSERT INTO document_vault (user_id, document_type, file_path)
            VALUES (%s, %s, %s)
        """, (user_id, document_type, file_path))

        db.commit()
        cursor.close()
        db.close()

        return JSONResponse({
            "status": "success",
            "file_path": file_path
        })

    except Exception as e:
        return JSONResponse({
            "status": "error",
            "message": str(e)
        })

class AddMemberRequest(BaseModel):
    guardian_id: int
    name: str
    phone: str
    relation: str

@app.post("/add_member")
def add_member(request: AddMemberRequest):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    try:
        # 1. Check if member already exists in guardians table (by phone)
        cursor.execute("SELECT id FROM guardians WHERE phone=%s", (request.phone,))
        existing = cursor.fetchone()

        if existing:
            member_id = existing["id"]
        else:
            # 2. Insert into guardians (new user)
            cursor.execute("""
                INSERT INTO guardians (name, phone, email, password)
                VALUES (%s, %s, %s, %s)
            """, (
                request.name,
                request.phone,
                f"{request.phone}@temp.com",   # temporary email
                "123456"                       # default password (change later)
            ))
            conn.commit()
            member_id = cursor.lastrowid

        # 3. Insert into family_memberss table
        cursor.execute("""
            INSERT INTO family_memberss (guardian_id, member_id, member_type, relation)
            VALUES (%s, %s, %s, %s)
        """, (
            request.guardian_id,
            member_id,
            "guardian",   # or 'user' depending on your app
            request.relation
        ))

        conn.commit()

        return {
            "status": "success",
            "message": "Member added successfully"
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

    finally:
        cursor.close()
        conn.close()
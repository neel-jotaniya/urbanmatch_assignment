# main.py
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from typing import List
import models, schemas

app = FastAPI()
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # Check if email already exists
    existing_user = db.query(models.User).filter(models.User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_dict = user.model_dump()

    db_user = models.User(**user_dict)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user

@app.get("/users/", response_model=List[schemas.User])
def read_users(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    users = db.query(models.User).offset(skip).limit(limit).all()
    return users

@app.get("/users/{user_id}", response_model=schemas.User)
def read_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# Task 1: Add User Update Endpoint
@app.put("/users/{user_id}", response_model=schemas.User)
def update_user(user_id: int, user_update: schemas.UserUpdate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    
    # Check if the user ID is valid
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if new email already exists
    if user_update.email and user_update.email != db_user.email:
        existing_user = db.query(models.User).filter(models.User.email == user_update.email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
    
    # Update user attributes
    update_data = user_update.model_dump(exclude_unset=True) 
    
    for key, value in update_data.items():
        setattr(db_user, key, value)
    
    db.commit()
    db.refresh(db_user)
    
    return db_user

# Task 2: Add User Deletion Endpoint
@app.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(db_user)
    db.commit()
    return {"message": "User deleted successfully"}

# Task 3: Endpoint to Find Matches for a User:
@app.get("/users/{user_id}/matches", response_model=List[schemas.User])
def find_matches(
    user_id: int,
    db: Session = Depends(get_db),
):
    # Fetch the user profile
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user_city = user.city
    user_interests = {interest for interest in user.interests}
    user_gender = user.gender
    user_age = user.age

    min_age = user_age - 5
    max_age = user_age + 5

    opposite_gender = "female" if user_gender == "male" else "male"


    # For given user Find users whose gender is opposite, live in same city, share at least one same interest, age difference is no more than 5 
    matches = (
        db.query(models.User)
        .filter(
            models.User.id != user_id,  # Exclude the current user
            models.User.city == user_city,  # Same city
            models.User.age.between(min_age, max_age),  # Within age range
            models.User.gender.ilike(opposite_gender),  # Opposite gender
        )
        .all()
    )
    filtered_matches = [
        match for match in matches if any(interest in user_interests for interest in match.interests) # Share at least one common interest
    ]
    
    return filtered_matches

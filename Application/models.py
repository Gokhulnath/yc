# models.py
from app import db
import uuid
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from datetime import datetime


class Batch(db.Model):
    __tablename__ = 'batches'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch = db.Column(db.String(255), nullable=False)
    batch_link = db.Column(db.Text, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    company_count = db.Column(db.Integer, default=0)
    companies = db.relationship('Company', backref='batch', lazy=True)


class Industry(db.Model):
    __tablename__ = 'industries'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    industry = db.Column(db.String(255), nullable=False)
    industry_link = db.Column(db.Text, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    company_count = db.Column(db.Integer, default=0)


class Company(db.Model):
    __tablename__ = 'companies'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    logo = db.Column(db.Text, nullable=False)
    company_name = db.Column(db.String(255), nullable=False)
    link = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(255))
    short_description = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    batch_id = db.Column(UUID(as_uuid=True), db.ForeignKey('batches.id'))
    tags = db.Column(ARRAY(db.Text))
    job_count = db.Column(db.String(50))
    domain = db.Column(db.Text)
    description = db.Column(db.Text)
    team_size = db.Column(db.String(50))
    primary_partner = db.Column(db.Text)
    linkedin = db.Column(db.Text)
    x = db.Column(db.Text)
    twitter = db.Column(db.Text)
    facebook = db.Column(db.Text)
    github = db.Column(db.Text)
    crunchbase = db.Column(db.Text)
    emails = db.Column(ARRAY(db.Text))
    worth = db.Column(db.Boolean, default=False)
    remarks = db.Column(db.Text)
    todo = db.Column(ARRAY(db.Text))

    industries = db.relationship('Industry', secondary='company_industries', backref='companies')
    people = db.relationship('Person', backref='company', lazy=True, cascade="all, delete-orphan")


class CompanyIndustry(db.Model):
    __tablename__ = 'company_industries'
    company_id = db.Column(UUID(as_uuid=True), db.ForeignKey('companies.id'), primary_key=True)
    industry_id = db.Column(UUID(as_uuid=True), db.ForeignKey('industries.id'), primary_key=True)


class Person(db.Model):
    __tablename__ = 'people'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = db.Column(UUID(as_uuid=True), db.ForeignKey('companies.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    designation = db.Column(db.String(255))
    linkedin = db.Column(db.Text)
    x = db.Column(db.Text)
    twitter = db.Column(db.Text)
    email = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

# routes.py
import json
from datetime import datetime

from app import app, db
from models import Company, Person, Batch, Industry, CompanyIndustry
from flask import render_template, request, redirect, url_for, jsonify
from sqlalchemy import func, or_
import ollama
import os
from flask import request, jsonify

# Constants for todo tags
TODO_TAGS = ['Emailed', 'inProgress', 'LinkedIn', 'Ignore', 'NotHiringNow']


@app.route('/')
def index():
    return render_template("index.html", todo_tags=TODO_TAGS)


@app.route('/api/companies')
def get_companies():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search_term = request.args.get('search', '')
    batch_id = request.args.get('batch_id', '')
    industry_id = request.args.get('industry_id', '')
    todo_tag = request.args.get('todo_tag', '')
    worth = request.args.get('worth', None)

    # Base query
    query = db.session.query(
        Company,
        func.count(Person.id).label('people_count')
    ).outerjoin(Person)

    # Apply filters
    if search_term:
        search_term = f"%{search_term.lower()}%"
        query = query.filter(
            or_(
                func.lower(Company.company_name).like(search_term),
                Company.id.in_(
                    db.session.query(Person.company_id).filter(
                        func.lower(Person.name).like(search_term)
                    )
                )
            )
        )

    if batch_id:
        query = query.filter(Company.batch_id == batch_id)

    if industry_id:
        query = query.filter(Company.id.in_(
            db.session.query(CompanyIndustry.company_id).filter(
                CompanyIndustry.industry_id == industry_id
            )
        ))

    if todo_tag:
        query = query.filter(Company.todo.contains([todo_tag]))

    if worth is not None:
        worth_bool = worth.lower() == 'true'
        query = query.filter(Company.worth == worth_bool)

    # Group by company
    query = query.group_by(Company.id)

    # Paginate
    total_count = query.count()
    companies_with_count = query.limit(per_page).offset((page - 1) * per_page).all()

    # Format response
    companies_data = []
    for company, people_count in companies_with_count:
        companies_data.append({
            'id': str(company.id),
            'logo': company.logo,
            'company_name': company.company_name,
            'short_description': company.short_description,
            'people_count': people_count,
            'todo': company.todo or [],
            'worth': company.worth
        })

    return jsonify({
        'companies': companies_data,
        'total': total_count,
        'page': page,
        'per_page': per_page,
        'total_pages': (total_count + per_page - 1) // per_page
    })


@app.route('/api/batches')
def get_batches():
    batches = Batch.query.order_by(Batch.year.desc()).all()
    return jsonify([{
        'id': str(batch.id),
        'name': batch.batch,
        'company_count': batch.company_count
    } for batch in batches])


@app.route('/api/industries')
def get_industries():
    industries = Industry.query.all()
    return jsonify([{
        'id': str(industry.id),
        'name': industry.industry,
        'company_count': industry.company_count
    } for industry in industries])


@app.route('/api/companies/<uuid:company_id>/toggle-worth', methods=['POST'])
def toggle_worth(company_id):
    company = Company.query.get_or_404(company_id)
    company.worth = not company.worth
    db.session.commit()
    return jsonify({'worth': company.worth})


@app.route('/company/<uuid:company_id>')
def company_detail(company_id):
    filter_params = {
        'search': request.args.get('search', ''),
        'batch_id': request.args.get('batch_id', ''),
        'industry_id': request.args.get('industry_id', ''),
        'todo_tag': request.args.get('todo_tag', ''),
        'worth': request.args.get('worth', None),
        'page': request.args.get('page', 1)
    }
    return render_template('company_detail.html', company_id=company_id,
                          filter_params=filter_params)


@app.route('/api/companies/<uuid:company_id>')
def get_company_detail(company_id):
    company = Company.query.get_or_404(company_id)
    people = Person.query.filter_by(company_id=company_id).all()

    company_data = {
        'id': str(company.id),
        'logo': company.logo,
        'company_name': company.company_name,
        'link': company.link,
        'location': company.location,
        'short_description': company.short_description,
        'description': company.description,
        'batch': company.batch.batch if company.batch else None,
        'tags': company.tags or [],
        'job_count': company.job_count,
        'domain': company.domain,
        'team_size': company.team_size,
        'primary_partner': company.primary_partner,
        'linkedin': company.linkedin,
        'x': company.x,
        'twitter': company.twitter,
        'facebook': company.facebook,
        'github': company.github,
        'crunchbase': company.crunchbase,
        'emails': company.emails or [],
        'worth': company.worth,
        'remarks': company.remarks,
        'todo': company.todo or [],
        'industries': [{'id': str(i.id), 'name': i.industry} for i in company.industries]
    }

    people_data = [{
        'id': str(person.id),
        'name': person.name,
        'email': person.email,
        'designation': person.designation,
        'linkedin': person.linkedin,
        'x': person.x,
        'twitter': person.twitter
    } for person in people]

    return jsonify({
        'company': company_data,
        'people': people_data
    })


@app.route('/api/companies/<uuid:company_id>/update', methods=['POST'])
def update_company_field(company_id):
    company = Company.query.get_or_404(company_id)
    data = request.json

    field = data.get('field')
    value = data.get('value')

    # Validate the field name to prevent security issues
    allowed_fields = ['remarks', 'todo']
    if field not in allowed_fields:
        return jsonify({'error': 'Invalid field name'}), 400

    # Update the field
    setattr(company, field, value)
    db.session.commit()

    return jsonify({
        'success': True,
        'field': field,
        'value': value
    })


# Add these routes to your routes.py file

@app.route('/api/people', methods=['POST'])
def add_person():
    data = request.json

    # Validate required fields
    if not data.get('name') or not data.get('company_id'):
        return jsonify({'error': 'Name and company_id are required'}), 400

    try:
        # Create new person
        person = Person(
            company_id=data.get('company_id'),
            name=data.get('name'),
            email=data.get('email'),
            designation=data.get('designation'),
            linkedin=data.get('linkedin'),
            x=data.get('x'),
            twitter=data.get('twitter')
        )

        db.session.add(person)
        db.session.commit()

        # Return the new person data
        return jsonify({
            'success': True,
            'person': {
                'id': str(person.id),
                'name': person.name,
                'email': person.email,
                'designation': person.designation,
                'linkedin': person.linkedin,
                'x': person.x,
                'twitter': person.twitter
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/people/<uuid:person_id>', methods=['PUT'])
def update_person(person_id):
    person = Person.query.get_or_404(person_id)
    data = request.json

    # Validate required fields
    if not data.get('name'):
        return jsonify({'error': 'Name is required'}), 400

    try:
        # Update person fields
        person.name = data.get('name')
        person.email = data.get('email')
        person.designation = data.get('designation')
        person.linkedin = data.get('linkedin')
        person.x = data.get('x')
        person.twitter = data.get('twitter')
        person.updated_at = datetime.utcnow()

        db.session.add(person)
        db.session.commit()

        # Return the updated person data
        return jsonify({
            'success': True,
            'person': {
                'id': str(person.id),
                'name': person.name,
                'email': person.email,
                'designation': person.designation,
                'linkedin': person.linkedin,
                'x': person.x,
                'twitter': person.twitter
            }
        })
    except Exception as e:
        db.session.rollback()
        print(str(e))
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate/linkedin', methods=['POST'])
def generate_linkedin_request():
    data = request.json
    company = data.get('company', {})
    additional_points = data.get('additional_points', '')

    # Hardcode the resume path
    resume_path = "static/Gokhulnath_Thirumaran_v3.txt"  # Assuming it's in the root directory

    # Read the resume content
    try:
        with open(resume_path, 'r') as file:
            resume_content = file.read()
    except FileNotFoundError:
        resume_content = "Resume file not found"

    # Construct the prompt for Ollama
    prompt = f"""
    You are a master's student in Computer Science at UIC in the US, actively seeking connections to explore internship opportunities.
    Use the resume content to authentically represent yourself: {resume_content}

    Generate a compelling LinkedIn connection request targeting professionals at {company.get('name')}.

    Company context:
    - Name: {company.get('name')}
    - Description: {company.get('description')}
    - Industry: {company.get('industry')}
    - Location: {company.get('location')}

    Key points to incorporate:
    - Mention your founding engineer experience at Chargebee microservice
    - Reference your entrepreneurial mindset and "figure it out" attitude
    - Express genuine interest in {company.get('name')}'s work
    - {additional_points}

    Start with "Hi," (no specific name needed)
    The connection message must be professional, engaging, and STRICTLY under 300 characters as LinkedIn has a hard character limit.
    Return ONLY the connection message text itself - no explanations, no quotation marks.

    Include a clear, brief call to action (like connecting to discuss potential opportunities).
    """

    try:
        # Call Ollama to generate the LinkedIn request
        response = ollama.generate(
            model='gemma3:4b',  # Use your preferred model
            prompt=prompt,
            options={
                'num_predict': 300  # Correct parameter for token limit
            }
        )

        # Extract and clean the generated text
        generated_text = response['response'].strip()

        # Ensure it's under 300 characters
        if len(generated_text) > 300:
            generated_text = generated_text[:297] + '...'

        return jsonify({
            'success': True,
            'text': generated_text,
            'length': len(generated_text)
        })

    except Exception as e:
        print(f"Error generating LinkedIn request: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/generate/email', methods=['POST'])
def generate_email():
    data = request.json
    company = data.get('company', {})
    additional_points = data.get('additional_points', '')

    # Hardcode the resume path
    resume_path = "static/Gokhulnath_Thirumaran_v3.txt"

    # Read the resume content
    try:
        with open(resume_path, 'r') as file:
            resume_content = file.read()
    except FileNotFoundError:
        resume_content = "Resume file not found"

    # Construct the enhanced prompt for Ollama with JSON output format
    prompt = f"""
    You are a personalized email writer for a master's student at UIC (University of Illinois at Chicago) seeking professional connections that could lead to internship opportunities.

    Resume details: {resume_content}

    Company information:
    - Name: {company.get('name')}
    - Description: {company.get('description')}
    - Industry: {company.get('industry')}
    - Location: {company.get('location')}

    Write a personalized, genuine email to founders at {company.get('name')} that accomplishes the following:

    1. Show genuine interest in their company by mentioning something specific you admire about their product, recent news, or company mission (reference their website if available)
    2. Briefly highlight 1-2 relevant skills/experiences from your background that specifically align with their company needs
    3. Demonstrate how you could add value (be specific about a problem you could help solve)
    4. Include a clear, low-commitment call to action (LinkedIn connection, brief reply, or 15-minute call)
    5. Acknowledge they may not be actively hiring, but express interest in building a relationship anyway
    6. Keep the tone warm yet professional, enthusiastic but not desperate

    Additional context to incorporate: {additional_points}

    DO NOT directly ask for a job or internship in the first email. Instead, focus on establishing a connection and offering value.

    Format your response as a JSON object with two fields: "subject" and "body".

    Examples of effective subject lines:
    - "Fellow [Industry] Enthusiast Interested in {company.get('name')}'s Innovative Work"
    - "UIC Master's Student with [Specific Skill] Hoping to Connect"
    - "Quick Question About {company.get('name')}'s Approach to [Relevant Challenge]"
    - "Impressed by {company.get('name')}'s [Recent Achievement] - Would Love to Connect"

    Examples of effective email openings:
    - "I've been following {company.get('name')}'s work on [specific project/product] and was particularly impressed by [specific feature/achievement]."
    - "Your recent [blog post/interview/product launch] about [topic] resonated with me, especially when you mentioned [specific point]."
    - "As someone passionate about [relevant field], I've admired how {company.get('name')} has been pioneering [specific approach/solution]."

    Examples of effective calls to action:
    - "I'd love to connect on LinkedIn [include profile link] - I regularly share insights about [relevant topic] that might interest you."
    - "Even if you're not currently hiring, I'd appreciate a quick 15-minute call to learn more about your work and share some ideas that might be valuable."
    - "I'll be attending [relevant upcoming event] - would you or someone from your team be there as well? It would be great to connect in person."
    - "All good if you're not hiring at the moment - I'd still love to connect and perhaps you could point me towards someone in your network who might benefit from my skills."

    Examples of value propositions:
    - "During my recent project at [organization], I developed a [specific solution] that improved [specific metric] by [result]. I see {company.get('name')} facing similar challenges with [issue], and I'd be excited to apply this approach to help solve it."
    - "My research at UIC focuses on [specific area], which aligns perfectly with your company's work on [related area]. I've actually developed [specific approach/tool] that could help address your current challenge with [specific issue mentioned on their website/social media]."
    - "I noticed from your job board that you value [specific skill/experience]. During my time at [previous role], I specialized in this area and [specific achievement/result]."

    Keep the entire email concise (350-500 words maximum) and make it feel personal, not templated. Do not hallucinate out of this scope, please refer the resume details for all details and provide details from that context only.
    Do not leave placeholders in the email rather fill the information.
    
    Gokhulnath Thirumaran
    +1 (312) 825-6933
    linkedin.com/in/gokhulnath-thirumaran
    gokhulnaththirumaran.com

    Example output format:
    {{
    "subject": "Master's Student & Founding Engineer Looking to Connect with YC Founders",
    "body": "Dear Founder,\n\nMy name is Gokhulnath Thirumaran, a Computer Science Master's student at the University of Illinois Chicago with a passion for building innovative technology from scratch. I've been following your journey since your company went through Y Combinator, and I'm impressed by what you've built.\n\nSince my freshman year of undergrad in 2019, I've lived by a simple philosophy: say yes to opportunities even when I don't have all the answers, then figure it out on the fly. This approach has led me to complete 20+ projects across various frameworks and technologies, starting when I barely knew how to code.\n\nAt Chargebee (a fintech unicorn), I served as a founding engineer for two internal startup microservices, building Atomic Pricing completely from scratch. I specifically chose these roles over established teams because I'm energized by creating something new rather than maintaining what already works.\n\nI'm reaching out because I believe I could bring value to [Company Name] through an internship opportunity. I understand early-stage startups often need people who can wear multiple hats and learn quickly - skills I've demonstrated throughout my career.\n\nAll good if you're not hiring at the moment! I'd still value connecting on LinkedIn (linkedin.com/in/gokhulnath-thirumaran) or even just a quick reply to say hi. If you have a few minutes, I'd also appreciate if you could check out my portfolio at gokhulnaththirumaran.com.\n\nAnd if you know other founders in your network who might be looking for someone with my builder mindset, I'd be grateful for an introduction.\n\nThank you for your time,\n\nGokhulnath Thirumaran\n+1 (312) 825-6933\ngokhulnaththirumaran.com"
    }}
    """

    try:
        # Call Ollama to generate the email
        response = ollama.generate(
            model='gemma3:4b',
            prompt=prompt
        )

        # Extract and parse the generated text as JSON
        generated_text = response['response'].strip()

        try:
            # Try to parse as JSON
            email_data = json.loads(generated_text)
            subject = email_data.get('subject', f"Regarding {company.get('name')}")
            body = email_data.get('body', generated_text)
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            print("Failed to parse JSON response, using fallback method")
            if "subject" in generated_text.lower() and "body" in generated_text.lower():
                # Try to extract using regex or string manipulation
                import re
                subject_match = re.search(r'"subject"\s*:\s*"([^"]+)"', generated_text)
                body_match = re.search(r'"body"\s*:\s*"([\s\S]+?)"(?:\s*}|$)', generated_text)

                subject = subject_match.group(1) if subject_match else f"Regarding {company.get('name')}"
                body = body_match.group(1).replace('\\n', '\n') if body_match else generated_text
            else:
                # Last resort fallback
                subject = f"Regarding {company.get('name')}"
                body = generated_text

        return jsonify({
            'success': True,
            'subject': subject,
            'body': body
        })

    except Exception as e:
        print(f"Error generating email: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

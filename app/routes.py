from app import app, db
from flask import render_template, request, flash, redirect, url_for
from app.forms import UserInfoForm, LoginForm, AddSiteForm, AddReportForm
from app.models import User, Report, Site, ReportUpdate, SiteUpdate, NewAction, NewDoc
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from app.scrape import InitialSiteScan, ReportUpdateScan

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    title = "SITE NAME | Sign Up"
    form = UserInfoForm()
    if request.method == 'POST' and form.validate():
        first_name = form.first_name.data 
        last_name = form.last_name.data 
        email = form.email.data 
        password = form.password.data 
        new_user = User(first_name, last_name, email, password)
        db.session.add(new_user)
        db.session.commit()
        flash("You have successfully signed up!", "success")
        return redirect(url_for('index'))
    return render_template('signup.html', title=title, form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    title = "SITE NAME | Sign Up"
    form = LoginForm()
    if request.method == 'POST' and form.validate():
        email = form.email.data 
        password = form.password.data 
        user = User.query.filter_by(email=email).first()
        if user is None or not check_password_hash(user.password, password):
            flash('Incorrect email or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        flash("Welcome back!", "success")
        return redirect(url_for('index'))
    return render_template('login.html', title=title, form=form)

@app.route('/logout')
def logout():
    logout_user()
    flash('See you next time!', 'primary')
    return redirect(url_for('index'))


@app.route('/addsite', methods=['GET', 'POST'])
@login_required
def addsite():
    title = "SITE NAME | Add a Site"
    site = Site()
    form = AddSiteForm()
    if request.method == 'POST' and form.validate():
        site_name = form.site_name.data
        gt_global_id = form.gt_global_id.data
        # This adds the new site to the Site table via User.sites, meaning the "user_id" value in the Site table will be the current user's
        new_site = Site(site_name=site_name, gt_global_id=gt_global_id)
        current_user.sites.append(new_site)
        db.session.add(new_site)
        db.session.commit()
        flash(f"{site_name} has been added to your sites!")
        return redirect(url_for("addsite"))
    return render_template("add_site.html", title=title, site=site, form=form)

@app.route('/addreport', methods=['GET', 'POST'])
@login_required
def addreport():
# You name the report, then you check any sites you want to add to the report
    title = "SITE NAME | Add a Report"
    report = Report()
    form = AddReportForm()
    if request.method == 'POST' and form.validate():
        report_name = form.report_name.data
        selected_sites = form.current_user_sites.data
        new_report = Report(report_name=report_name, sites=selected_sites)
        current_user.reports.append(new_report)
        db.session.add(new_report)
        db.session.commit()
        sites_list = [[site.id, site.gt_global_id] for site in new_report.sites]
        initial_site_scan = InitialSiteScan(sites_list, new_report.id)
        initial_site_scan.start()
        flash(f"{report_name} has been added to your sites!")
        return redirect(url_for("addreport"))
    return render_template("add_report.html", title=title, report=report, form=form)


@app.route('/mysites')
@login_required
def mysites():
    context = {
        'title': 'SITE NAME | My Sites',
        'my_sites': Site.query.filter_by(user_id=current_user.id).all()
    }
    return render_template('my_sites.html', **context)


@app.route('/myreports', methods=["GET", "POST"])
@login_required
def myreports():
    my_reports = Report.query.filter_by(user_id=current_user.id).all()
    context = {
        'title': 'SITE NAME | My Reports',
        'my_reports': my_reports,
        'ReportUpdateScan': ReportUpdateScan
    }
    if request.method == "POST":
        for i in range(len(my_reports)):
            if request.form.get(f"report_id{my_reports[i].id}"):
                new_scan = ReportUpdateScan(my_reports[i].id)
                new_scan.start()
                flash(f"We've prepared an update for {my_reports[i].report_name}!")
                return redirect(url_for("myreports"))
    return render_template('my_reports.html', **context)



@app.route('/myreports/<int:report_id>')
@login_required
def report_details(report_id):
    report = Report.query.get_or_404(report_id)
    report_updates = report.report_updates
    sites_list = [report.sites[i].gt_global_id for i in range(len(report.sites))]
    context = {
        'title': f'SITE NAME | {report.report_name}'
    }
    return render_template('report_details.html', report=report, report_updates=report_updates)

    # {% set sites_list = [] %}
    # {% for site in r.sites %}
    #     {% for  %}
    #     {% do sites_list.append([{{site.id}}, {{site.gt_global_id}}]) %}
    # {% endfor %}
    # {% sites_list = [[site.id, site.gt_global_id] for site in r.sites] %} 

@app.route('/myreports/<int:report_id>/<int:report_update_id>')
@login_required
def report_update(report_id, report_update_id):
    # THIS ONLY GIVES YOU INFO ON THE SITES THAT HAD NEW ACTIONS IN THE UPDATE. YOU NEED TO CREATE A CONDITIONAL IN 
    # report_update.html FOR SITES WITH NO UPDATES IN THE REPORT UPDATE
    report = Report.query.get_or_404(report_id)
    report_update = ReportUpdate.query.get_or_404(report_update_id)
    site_updates = report_update.site_updates
    site_update_ids = [site_update.id for site_update in site_updates]
    sites_list = [[site.site_id, Site.query.filter_by(id=site.site_id).first().gt_global_id] for site in site_updates]
    context = {
        'title': f'SITE NAME | {report.report_name} - {report_update.scraped_on} Report',
        'report': report,
        'report_update': report_update,
        'Site': Site(),
        'site_updates': site_updates
    }
    return render_template('report_update.html', **context)



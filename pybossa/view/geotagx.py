# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2015 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.
""" Custom Geotagx functionalities for Pybossa"""
from flask import Blueprint, request, url_for, flash, redirect, session, \
	current_app, render_template, abort, request
from pybossa.model.user import User
from pybossa.model.task_run import TaskRun
from pybossa.model.task import Task
from pybossa.model.project import Project
from pybossa.util import Pagination, pretty_date
from pybossa.core import db
from pybossa.cache import users as cached_users
from pybossa.cache import projects as cached_projects
from pybossa.view import projects as projects_view
from flask_oauthlib.client import OAuthException
from flask.ext.login import login_required, login_user, logout_user, current_user
from flask import jsonify

blueprint = Blueprint('geotagx', __name__)

def setup_geotagx_config_default_params():
	""" Sets up default values for geotagx specific config params """
	if "GEOTAGX_FINAL_SURVEY_TASK_REQUIREMENTS" not in current_app.config.keys():
		current_app.config['GEOTAGX_FINAL_SURVEY_TASK_REQUIREMENTS'] = 30

@blueprint.route('/get_geotagx_survey_status')
def get_geotagx_survey_status():
	""" Get geotagx survey status  """
	""" Used by client side javascript code to determine rendering of the different surveys """
	if not current_user.is_anonymous():
		result = {}
		if "geotagx_survey_status" in current_user.info.keys():
			rank_and_score = cached_users.rank_and_score(current_user.id)
			result['geotagx_survey_status'] = current_user.info['geotagx_survey_status']
			result['task_runs'] = rank_and_score['score']
			setup_geotagx_config_default_params()
			result['final_survey_task_requirements'] = current_app.config['GEOTAGX_FINAL_SURVEY_TASK_REQUIREMENTS']
		else:
			result['geotagx_survey_status'] = "RESPONSE_NOT_TAKEN"

		return jsonify(result)
	else:
		return jsonify({'result':' -_- STOP SNOOPING AROUND -_- '})

@blueprint.route('/update_geotagx_survey_status')
def update_geotagx_survey_status():
	""" Updates Geotagx Survey Status for the current user """
	""" Used by client side javascript code to update surveys states for the current_user """	
	previous_state = request.args.get('previous_geotagx_survey_state')
	new_state = request.args.get('new_geotagx_survey_state')
	if not current_user.is_anonymous():
		valid_options = ["RESPONSE_NOT_TAKEN", "AGREE_TO_PARTICIPATE", "DENY_TO_PARTICIPATE", "DENY_TO_PARTICIPATE_IN_FINAL_SURVEY", "ALL_SURVEYS_COMPLETE" ]
		# Check if both the parameters are indeed valid options
		if (new_state in valid_options) and (previous_state in valid_options) :
			# and ((previous_state == current_user.info['geotagx_survey_status']) or (previous_state == "RESPONSE_NOT_TAKEN")) 
			current_user.info['geotagx_survey_status'] = new_state
			db.session.commit()
			return jsonify({'result':True})
		else:
			return jsonify({'result':' -_- STOP SNOOPING AROUND -_- '})	
	else:
		return jsonify({'result':' -_- STOP SNOOPING AROUND -_-'})

@blueprint.route('/survey')
def render_survey():
	""" Renders appropriate survey for current user or redirects to home page if surveys are not applicable """
	if not current_user.is_anonymous():
		rank_and_score = cached_users.rank_and_score(current_user.id)
		survey_type = "INITIAL"
		setup_geotagx_config_default_params()
		if rank_and_score['score'] > current_app.config['GEOTAGX_FINAL_SURVEY_TASK_REQUIREMENTS'] and "geotagx_survey_status" in current_user.info.keys() and current_user.info['geotagx_survey_status'] == "AGREE_TO_PARTICIPATE" :
			survey_type = "FINAL"

		if "geotagx_survey_status" in current_user.info.keys() and current_user.info['geotagx_survey_status'] in ["DENY_TO_PARTICIPATE", "DENY_TO_PARTICIPATE_IN_FINAL_SURVEY", "ALL_SURVEYS_COMPLETE"]:
			survey_type = "NONE"

		return render_template('/geotagx/surveys/surveys.html', survey_type = survey_type, GEOTAGX_FINAL_SURVEY_TASK_REQUIREMENTS = current_app.config['GEOTAGX_FINAL_SURVEY_TASK_REQUIREMENTS'])
	else:
		return redirect(url_for('home.home'))

@blueprint.route('/users/delete/<name>/<confirmed>', methods = ['GET'])
@blueprint.route('/users/delete/<name>', defaults={'confirmed':'unconfirmed'}, methods = ['GET'])
def delete_user(name, confirmed):
	"""
	Deletes a user on pybossa
	- Only admins will be able to delete other users.
	- Does not let delete admin users.
		Admin users will have to remove the user from the admin lists before they can delete then
	- Marks all the task_runs of the specific user as anonymous
	- Changes the ownership of all the projects owned by the user to the current_user
	TODO: Clean this feature up and push this feature to pybossa core
	"""

	"""
	Get the user object and contributed projects object from cache to enable
	global helper functions to render it in a uniform way.
	But Obtain the results from the non-memoized functions to get the latest state
	"""
	target_user = cached_users.get_user_summary(name)
	if current_user.admin and target_user != None and current_user.id != target_user['id'] :

		user_page_redirect = request.args.get('user_page_redirect')
		if not user_page_redirect:
			user_page_redirect = 1

		if confirmed == "unconfirmed":
			published_projects = cached_users.published_projects(target_user['id'])
			draft_projects = cached_users.draft_projects(target_user['id'])
			hidden_projects = cached_users.hidden_projects(target_user['id'])
			owned_projects = published_projects + draft_projects + hidden_projects

			return render_template('geotagx/users/delete_confirmation.html', \
														target_user = target_user,
														owned_projects = owned_projects,
														user_page_redirect=user_page_redirect
														)
		elif confirmed == "confirmed":
			"""
				Retrieval of the User object necessary as the target_user object
				obtained from `cached_users.get_user_summary` doesnot expose
				the `admin` check that is necessary to prevent the user from
				deleting other admin users, and also the SQLAlchemy `delete`
				function
			"""
			user_object = User.query.filter_by(id=target_user['id']).first()
			if user_object.admin:
				# It is not allowed to delete other admin users
				abort(404)

			"""
				Mark all task runs by the user as anonymous
				Mark the user_ip field in the task_run by the username instead
				to retain user identity for analytics
			"""
			task_runs = TaskRun.query.filter_by(user_id=target_user['id']).all()
			for task_run in task_runs:
				task_run.user_id = None
				task_run.user_ip = "deleted_user_"+target_user['name']
				db.session.commit()

			"""
				Change the ownership of all projects owned by the target user
				to that of the current user
			"""
			projects = Project.query.filter_by(owner_id=target_user['id']).all()
			for project in projects:
				project.owner_id = current_user.id
				db.session.commit()
				"""
					Clean cached data about the project
				"""
				cached_projects.clean_project(project.id)

			"""
				Delete the user from the database
			"""
			db.session.delete(user_object)
			db.session.commit()

			"""
				Clean user data from the cache
				Force Update current_user's data in the cache
			"""
			cached_users.delete_user_summary(target_user['id'])
			cached_users.delete_user_summary(current_user.id)

			flash("User <strong>"+target_user['name']+"</strong> has been successfully deleted, and all the projects owned by the user have been transferred to you.", 'success')
			return redirect(url_for('geotagx.users_page', page=user_page_redirect))
		else:
			abort(404)
	else:
		abort(404)

@blueprint.route('/users/', defaults={'page': 1})
@blueprint.route('/users/page/<int:page>')
def users_page(page):
    """
    Admin page for all PyBossa registered users.
    Returns a Jinja2 rendered template with the users.

    Note ::
    This would be an admin only page, hence, rendering cached data
    not necessary. Instead the admin would rather want the most updated data
    """
    per_page = 24
    pagination = User.query.paginate(page, per_page, False)
    accounts = pagination.items
    count = pagination.total

    """
    Normalize accounts for it to be rendered by the global helper functions we use in the theme
    """
    for k in accounts:
		k.n_task_runs = len(k.task_runs)
		k.registered_ago = pretty_date(k.created)

    if not accounts and page !=1 and not current_user.admin:
        abort(404)

    if current_user.is_authenticated():
        user_id = current_user.id
    else:
        user_id = 'anonymous'
    return render_template('geotagx/users/index.html', accounts = accounts,
                           total = count, pagination_page = str(page),
                           title = "Community", pagination = pagination)


@blueprint.route('/project/<project_short_name>/flush_task_runs', defaults={'confirmed':'unconfirmed'})
@blueprint.route('/project/<project_short_name>/flush_task_runs/<confirmed>')
def flush_task_runs(project_short_name, confirmed):
	project = cached_projects.get_project(project_short_name)
	if current_user.admin or project.owner_id == current_user.id:
		if confirmed == "confirmed":
			associated_task_runs = TaskRun.query.filter_by(project_id=project.id).all()
			for task_run in associated_task_runs:
				db.session.delete(task_run)
				pass
			db.session.commit()

			# Iterate over all tasks associated with the project, and mark them as 'ongoing'
			# Some tasks might be marked as 'completed' if enough task_runs were done
			associated_tasks = Task.query.filter_by(project_id=project.id).all()
			for task in associated_tasks:
				if task.state != u"ongoing":
					task.state = u"ongoing"
					db.session.commit()

			# Reset project data in the cache
			cached_projects.clean_project(project.id)
			# Note: The cache will hold the old data about the users who contributed
			# to the tasks associated with this projects till the User Cache Timeout.
			# Querying the list of contributors to this project, and then individually updating
			# their cache after that will be a very expensive query, hence we will avoid that
			# for the time being.
			flash('All Task Runs associated with this project have been successfully deleted.', 'success')
			return redirect(url_for('project.task_settings', short_name = project_short_name))
		elif confirmed == "unconfirmed":
			# Obtain data required by the project profile renderer
		    (project, owner, n_tasks, n_task_runs,
		     overall_progress, last_activity) = projects_view.project_by_shortname(project_short_name)
		    return render_template('geotagx/projects/delete_task_run_confirmation.html',
		                           project=project,
		                           owner=owner,
		                           n_tasks=n_tasks,
		                           n_task_runs=n_task_runs,
		                           overall_progress=overall_progress,
		                           last_activity=last_activity,
		                           n_completed_tasks=cached_projects.n_completed_tasks(project.id),
		                           n_volunteers=cached_projects.n_volunteers(project.id))
		else:
			abort(404)
	else:
		abort(404)
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
from flask import Blueprint, request, url_for, flash, redirect, session, current_app, render_template
from pybossa.model.user import User
from pybossa.core import db
from pybossa.cache import users as cached_users
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

		if current_user.info['geotagx_survey_status'] in ["DENY_TO_PARTICIPATE", "DENY_TO_PARTICIPATE_IN_FINAL_SURVEY", "ALL_SURVEYS_COMPLETE"]:
			survey_type = "NONE"

		return render_template('/geotagx/surveys/surveys.html', survey_type = survey_type, GEOTAGX_FINAL_SURVEY_TASK_REQUIREMENTS = current_app.config['GEOTAGX_FINAL_SURVEY_TASK_REQUIREMENTS'])
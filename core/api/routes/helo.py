"""
# PURPOSE: API endpoints to control and inspect AJA HELO schedules and devices
# DEPENDENCIES: Flask, flask_restx, Flask-Limiter, core.services.helo
# MODIFICATION NOTES: v1 - minimal control endpoints
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_restx import Namespace, Resource, fields
from flask_limiter.util import get_remote_address

from core.services import HeloService


def create_helo_blueprint(limiter):
    bp = Blueprint('helo', __name__)
    ns = Namespace('helo', description='AJA HELO integration')

    service = HeloService()

    schedule_model = ns.model('HeloSchedule', {
        'id': fields.Integer,
        'device_id': fields.Integer,
        'cablecast_show_id': fields.Integer,
        'start_time': fields.DateTime,
        'end_time': fields.DateTime,
        'action': fields.String,
        'status': fields.String,
    })

    @ns.route('/sync')
    class HeloSync(Resource):
        decorators = [limiter.limit("10/minute", key_func=get_remote_address)]

        def post(self):
            devices = service.upsert_devices_from_config()
            plans = service.build_plans_from_cablecast()
            created = service.sync_helo_schedules(plans)
            return jsonify({'devices': devices, 'schedules': created})

    @ns.route('/trigger')
    class HeloTrigger(Resource):
        decorators = [limiter.limit("30/minute", key_func=get_remote_address)]

        def post(self):
            result = service.trigger_due_actions()
            return jsonify(result)

    bp_ns = ns
    return bp, bp_ns



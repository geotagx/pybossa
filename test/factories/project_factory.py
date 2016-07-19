# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2015 SciFabric LTD.
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

from pybossa.model.project import Project
from . import BaseFactory, factory, project_repo


class ProjectFactory(BaseFactory):
    class Meta:
        model = Project

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        project = model_class(*args, **kwargs)
        project_repo.save(project)
        return project

    id = factory.Sequence(lambda n: n)
    name = factory.Sequence(lambda n: u'My (utf8=✓)Project number %d' % n)
    short_name = factory.Sequence(lambda n: u'✓project%d' % n)
    description = u'Project description utf8=✓'
    allow_anonymous_contributors = True
    featured = False
    published = True
    webhook = None
    owner = factory.SubFactory('factories.UserFactory')
    owner_id = factory.LazyAttribute(lambda project: project.owner.id)
    category = factory.SubFactory('factories.CategoryFactory')
    category_id = factory.LazyAttribute(lambda project: project.category.id)
    info = {'task_presenter': '<div>utf8=✓</div>'}

# Copyright 2013 Diego Orzaez, Univ.Politecnica Valencia, Consejo Superior de
# Investigaciones Cientificas
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from django.conf.urls import patterns, url
from goldenbraid.views.feature import (add_feature_view, feature_view,
                                       add_vector_view)

from goldenbraid.views.api import(feature_uniquenames, features_children,
                                  features_key_elements)

from goldenbraid.views.feature_search import search_features_view
from goldenbraid.views.multipartite import (multipartite_view,
                                            multipartite_protocol_view,
                                            multipartite_view_genbank,
                                            multipartite_view_free,
                                            multipartite_view_free_genbank,
                                            multipartite_view_free_protocol,
                                            multipartite_view_add)
from goldenbraid.views.bipartite import (bipartite_view,
                                         bipartite_view_genbank,
                                         bipartite_view_protocol,
                                         bipartite_view_add)
from goldenbraid.views.domestication import (domestication_view,
                                             domestication_view_genbank,
                                             domestication_view_protocol,
                                             domestication_view_add,
                                             synthesis_view,
                                             synthesis_view_genbank,
                                             synthesis_view_protocol)
from goldenbraid.views.experiment import (search_experiment,
                                          add_experiment_view, experiment_view)


urlpatterns = patterns('',
                       url(r'^add/vector/$', add_vector_view,
                           name='add_vector'),
                       url(r'^add/feature/$', add_feature_view,
                           name='add_feature'),
                       url(r'^add/experiment/$', add_experiment_view,
                           name='add_experiment'),
                       url(r'^experiment/(?P<uniquename>.+)/$',
                           experiment_view, name='experiment_view'),
                       url(r'^search/experiment/$', search_experiment,
                           name='search_experiments'),
                       url(r'^search/features/$', search_features_view,
                           name='search_features'),
                       url(r'^feature/(?P<uniquename>.+)/$', feature_view,
                           name='feature_view'),
                       url(r'^do/multipartite/add/?$', multipartite_view_add,
                           name="multipartite_view_add"),
                       url(r'^do/multipartite/free/protocol/?$',
                           multipartite_view_free_protocol,
                           name="multipartite_view_free_protocol"),
                       url(r'^do/multipartite/free/genbank/?$',
                           multipartite_view_free_genbank,
                           name="multipartite_view_free_genbank"),
                       url(r'^do/multipartite/free/(?P<form_num>.+)?/?$',
                           multipartite_view_free,
                           name="multipartite_view_free"),
                       url(r'^do/multipartite/protocol/$',
                           multipartite_protocol_view,
                           name="multipartite_view_protocol"),
                       url(r'^do/multipartite/(?P<multi_type>.+)?/genbank/$',
                           multipartite_view_genbank,
                           name="multipartite_view_genbank"),
                       url(r'^do/multipartite/(?P<multi_type>.+)?/?$',
                           multipartite_view,
                           name='multipartite_view'),
                       url(r'^do/bipartite/add/?$', bipartite_view_add,
                           name='bipartite_view_add'),
                       url(r'^do/bipartite/genbank/?$', bipartite_view_genbank,
                           name='bipartite_view_genbank'),
                       url(r'^do/bipartite/protocol/?$',
                           bipartite_view_protocol,
                           name='bipartite_view_protocol'),
                       url(r'^do/bipartite/(?P<form_num>.+)?/?$',
                           bipartite_view,
                           name='bipartite_view'),
                       url(r'^do/domestication/add/$', domestication_view_add,
                           name='domestication_view_add'),
                       url(r'^do/domestication/genbank/$',
                           domestication_view_genbank,
                           name='domestication_view_genbank'),
                       url(r'^do/domestication/protocol/$',
                           domestication_view_protocol,
                           name='domestication_view_protocol'),
                       url(r'^do/domestication/$', domestication_view,
                           name='domestication_view'),
                       url(r'^do/synthesis/$', synthesis_view,
                           name='synthesis_view'),
                       url(r'^do/synthesis/genbank/$', synthesis_view_genbank,
                           name='shinthesis_view_genbank'),
                       url(r'^do/synthesis/protocol/$',
                           synthesis_view_protocol,
                           name='synthesis_view_protocol'),
                       url('api/feature_uniquenames/$',
                           feature_uniquenames,
                           name='api_feature'),
                       url('api/features_children/$',
                           features_children,
                           name='api_feature_children'),
                       url('api/features_key_elements/$',
                           features_key_elements,
                           name='feature_key_elements'),
                       )

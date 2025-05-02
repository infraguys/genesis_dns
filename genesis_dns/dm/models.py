#    Copyright 2025 Genesis Corporation.
#
#    All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from oslo_config import cfg
from restalchemy.common import contexts
from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import relationships
from restalchemy.dm import types
from restalchemy.storage.sql import orm

from genesis_dns.common import constants as c


CONF = cfg.CONF


class CommonModel(
    models.ModelWithTimestamp,
    models.ModelWithUUID,
    orm.SQLStorableMixin,
):
    pass


class Domain(CommonModel, models.ModelWithProject):
    __tablename__ = "domains"
    name = properties.property(types.String(), required=True)
    last_check = properties.property(types.Integer(), default=None)
    notified_serial = properties.property(types.Integer(), default=None)
    # Used only for PDNS
    id = properties.property(types.Integer())
    # Next columns exist in DB but used only for PDNS support and have
    #  sane defaults.
    # id = properties.property(types.Integer())
    # type = properties.property(types.Enum(("PRIMARY", "SLAVE")), required=True)
    # master = properties.property(types.String(), default=None)
    # account = properties.property(types.String(), default=None)
    # options = properties.property(types.Text(), default=None)
    # catalog = properties.property(types.Text(), default=None)
    # project_id = properties.property(types.UUID(), required=True)

    @classmethod
    def get_next_domain_id(cls, session=None):
        session = session or contexts.Context().get_session()
        return session.execute(
            "SELECT nextval('domain_id_seq') as val"
        ).fetchall()[0]["val"]

    def __init__(self, session=None, **kwargs):
        super().__init__(id=self.get_next_domain_id(session=session), **kwargs)

    def insert(self, session=None):
        # TODO: to be public autoritative DNS, we need:
        #  - make sure the SOA record is correct (serial, too, for zone transfers)
        #    (or don't update serial, it's needed only for secondary DNS replicaion,
        #     we can just don't support it, route53 doesn't support it either)
        super().insert(session=session)
        # TODO: make default soa record configurable
        # TODO: set soa serial as date, see ya.ru for example
        soa = Record(
            domain=self,
            name=self.name,
            type="SOA",
            content=f"a.misconfigured.dns.server.invalid {self.name} 0 10800 3600 604800 3600",
        )
        soa.save(session=session)


# TODO: configure powerdns to not even try to read domainmetadata?
# NOTE: Powerdns checks settings per each domain, non-existent row is ok too,
#  so just don't implement it if not needed.
# class DomainMetadata:
#    __tablename__ = "domainmetadata"


class Record(CommonModel):
    __tablename__ = "records"
    domain = relationships.relationship(Domain, required=True)
    domain_id = properties.property(types.Integer())
    name = properties.property(types.String(), required=True)
    type = properties.property(
        types.Enum(("A", "AAAA", "CNAME", "MX", "TXT", "SOA")), required=True
    )
    content = properties.property(types.String(), required=True)
    ttl = properties.property(types.Integer(), required=True, default=3600)
    prio = properties.property(types.Integer(), default=None)
    disabled = properties.property(types.Boolean(), default=False)
    # Next columns exist in DB but used only for PDNS support and have
    #  sane defaults.
    # domain_id = properties.property(types.Integer())
    # ordername = properties.property(types.String(), default=None)
    # auth = properties.property(types.Boolean(), default=True)

    def __init__(self, domain, **kwargs):

        super().__init__(domain=domain, domain_id=domain.id, **kwargs)

    # TODO:
    #  - restrict SOA deletion
    #  - validate different record types

from . import ashby, greenhouse, lever, remoteok, remotive

PROVIDERS = {
    remotive.ID: remotive,
    remoteok.ID: remoteok,
    greenhouse.ID: greenhouse,
    lever.ID: lever,
    ashby.ID: ashby,
}

ATS_PROVIDERS = (greenhouse, lever, ashby)

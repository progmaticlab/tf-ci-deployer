import org.sonatype.nexus.blobstore.api.BlobStoreManager
import org.sonatype.nexus.repository.config.Configuration
import org.sonatype.nexus.repository.storage.WritePolicy
import org.sonatype.nexus.repository.maven.VersionPolicy
import org.sonatype.nexus.repository.maven.LayoutPolicy


// Useful links 
// https://github.com/sonatype/nexus-public/blob/master/plugins/nexus-script-plugin/src/main/java/org/sonatype/nexus/script/plugin/internal/provisioning/RepositoryApiImpl.groovy
// https://github.com/sonatype/nexus-public/tree/master/components/nexus-security/src/main/java/org/sonatype/nexus/security


def delete_repo(name) {
    def repoManager = repository.getRepositoryManager()
    def existingRepository = repoManager.get(name)
    if (existingRepository != null) {
        repoManager.delete(name)
    }
}

def create_or_update_repo(name, configuration) {
    def repoManager = repository.getRepositoryManager()
    def existingRepository = repoManager.get(name)
    if (existingRepository != null) {
        log.info("Update repo {}".format(name))
        existingRepository.stop()
        // ===
        // leads to error in UI: https://github.com/savoirfairelinux/ansible-nexus3-oss/issues/38
        // existingRepository.update(configuration)
        def new_config = existingRepository.getConfiguration().copy()
        new_config.setAttributes(configuration.getAttributes())
        existingRepository.update(new_config)
        // ===
        existingRepository.start()
    } else {
        log.info("Create repo {}".format(name))
        repoManager.create(configuration)
    }
}

def get_docker_opts(port) {
    def docker_opts = [
        httpPort: port,
        v1Enabled : true,
        forceBasicAuth: false
    ]
    return docker_opts
}

def get_storage_opts(write_policy = WritePolicy.ALLOW) {
    def storage_opts = null
    if (write_policy != null) {
        storage_opts =  [
            writePolicy: write_policy,
            blobStoreName: BlobStoreManager.DEFAULT_BLOBSTORE_NAME,
            strictContentTypeValidation: false
        ]
    } else {
        storage_opts =  [
            blobStoreName: BlobStoreManager.DEFAULT_BLOBSTORE_NAME,
            strictContentTypeValidation: false
        ]
    }
    return storage_opts
}

def get_httpclient_opts() {
    def httpclient_opts = [
        blocked: false,
        autoBlock: false,
        connection: [
            useTrustStore: false
        ]
    ]
    return httpclient_opts
}

def get_proxy_opts(remote) {
    def proxy_opts = [
        remoteUrl: remote,
        contentMaxAge: 1440,
        metadataMaxAge: 1440
    ]
    return proxy_opts
}

def get_negative_cache_opts() {
    def negative_cache_opts =   [
        enabled: true,
        timeToLive: 1440
    ]
    return negative_cache_opts
}

def get_maven_opts() {
    def maven_opts = [
        versionPolicy: VersionPolicy.RELEASE,
        layoutPolicy : LayoutPolicy.PERMISSIVE
    ]
    return maven_opts
}

def get_cleanup(name) {
    def cleanup_opts = [
        policyName: name
    ] as Map
    return cleanup_opts
}

def create_docker_hosted(name, port, cleanup=null) {
    def attrs = [
            docker: get_docker_opts(port),
            storage: get_storage_opts(),
    ] as Map
    if (cleanup != null) {
        attrs['cleanup'] = get_cleanup(cleanup)
    }
    def configuration = new Configuration(
        repositoryName: name,
        recipeName: 'docker-hosted',
        online: true,
        attributes: attrs
    )
    create_or_update_repo(name, configuration)
}

def create_docker_proxy(name, port, remote) {
    configuration = new Configuration(
        repositoryName: name,
        recipeName: 'docker-proxy',
        online: true,
        attributes: [
            docker: get_docker_opts(port),
            proxy: get_proxy_opts(remote),
            dockerProxy: [
                indexType: 'HUB',
                useTrustStoreForIndexAccess: true
            ],
            httpclient: get_httpclient_opts(),
            storage: get_storage_opts(null),
            negativeCache: get_negative_cache_opts(),
        ]
    )
    create_or_update_repo(name, configuration)
}

def create_pypi_proxy(name, remote) {
    configuration = new Configuration(
        repositoryName: name,
        recipeName: 'pypi-proxy',
        online: true,
        attributes: [
            proxy: get_proxy_opts(remote),
            httpclient: get_httpclient_opts(),
            storage: get_storage_opts(null),
            negativeCache: get_negative_cache_opts()
        ]
    )
    create_or_update_repo(name, configuration)
}

def create_raw_hosted(name) {
    configuration = new Configuration(
        repositoryName: name,
        recipeName: 'raw-hosted',
        online: true,
        attributes: [
            storage: get_storage_opts(),
        ]
    )
    create_or_update_repo(name, configuration)
}

def create_raw_proxy(name, remote) {
    configuration = new Configuration(
        repositoryName: name,
        recipeName: 'raw-proxy',
        online: true,
        attributes: [
            proxy: get_proxy_opts(remote),
            httpclient: get_httpclient_opts(),
            storage: get_storage_opts(null),
            negativeCache: get_negative_cache_opts()
        ]
    )
    create_or_update_repo(name, configuration)
}

def create_yum_hosted(name, depth) {
    configuration = new Configuration(
        repositoryName: name,
        recipeName: 'yum-hosted',
        online: true,
        attributes: [
            yum: ['repodataDepth': depth] as Map,
            storage: get_storage_opts(),
        ]
    )
    create_or_update_repo(name, configuration)
}

def create_yum_proxy(name, remote) {
    configuration = new Configuration(
        repositoryName: name,
        recipeName: 'yum-proxy',
        online: true,
        attributes: [
            proxy: get_proxy_opts(remote),
            httpclient: get_httpclient_opts(),
            storage: get_storage_opts(null),
            negativeCache: get_negative_cache_opts()
        ]
    )
    create_or_update_repo(name, configuration)
}

def create_maven_hosted(name) {
    configuration = new Configuration(
        repositoryName: name,
        recipeName: 'maven2-hosted',
        online: true,
        attributes: [
            maven: get_maven_opts(),
            storage: get_storage_opts()
        ]
    )
    create_or_update_repo(name, configuration)
}

def create_maven_proxy(name, remote) {
    configuration = new Configuration(
        repositoryName: name,
        recipeName: 'maven2-proxy',
        online: true,
        attributes: [
            maven: get_maven_opts(),
            proxy: get_proxy_opts(remote),
            httpclient: get_httpclient_opts(),
            storage: get_storage_opts(null),
            negativeCache: get_negative_cache_opts()
        ]
    )
    create_or_update_repo(name, configuration)
}

def create_maven_group(name, members) {
    configuration = new Configuration(
        repositoryName: name,
        recipeName: 'maven2-proxy',
        online: true,
        attributes: [
            group: [
                memberNames: members
            ],
            storage: get_storage_opts(null),
        ]
    )
    create_or_update_repo(name, configuration)
}

// Docker
// Hosted
delete_repo('tungsten_ci')
create_docker_hosted('tungsten_ci', 5001, 'tf-cleanup-policy')
create_docker_hosted('tungsten_gate_cache', 5002)
// unknown now
// create_docker_hosted('tungsten_nightly', 5003)
// create_docker_hosted('access', 5004)
// Proxy
create_docker_proxy('proxy', 5005, 'https://registry-1.docker.io')

// PyPI
// Proxy
create_pypi_proxy('pypi', 'https://pypi.org')

// Raw
// Hosted
create_raw_hosted('contrail-ubuntu')
create_raw_hosted('images')
create_raw_hosted('documentation')
// Proxy
create_raw_proxy('ubuntu', 'http://ubuntu.mirror.vexxhost.com/ubuntu')
create_raw_proxy('contrail-third-party', 'http://148.251.5.90/contrail-third-party')

// Yum
// Proxy
create_yum_proxy('docker-ce-stable',    'https://download.docker.com/linux/centos/7/x86_64/stable')
create_yum_proxy('google-chrome',       'http://dl.google.com/linux/chrome/rpm/stable/x86_64')
create_yum_proxy('openstack-newton',    'http://mirror.neu.edu.cn/centos/7/cloud/x86_64/openstack-newton')
create_yum_proxy('openstack-ocata',     'http://mirror.centos.org/centos/7/cloud/x86_64/openstack-ocata')
create_yum_proxy('openstack-queens',    'http://mirror.centos.org/centos/7/cloud/x86_64/openstack-queens')
create_yum_proxy('openstack-rocky',     'http://mirror.centos.org/centos/7/cloud/x86_64/openstack-rocky')
create_yum_proxy('epel',                'https://dl.fedoraproject.org/pub/epel/7/x86_64')
create_yum_proxy('centos7-os',          'http://centos.mirror.vexxhost.com/7/os/x86_64')
create_yum_proxy('centos7-updates',     'http://centos.mirror.vexxhost.com/7/updates/x86_64')
create_yum_proxy('centos7-extras',      'http://centos.mirror.vexxhost.com/7/extras/x86_64')
create_yum_proxy('centos7-centosplus',  'http://centos.mirror.vexxhost.com/7/centosplus/x86_64')
// hosted tpc binary has third party packages that was taken somewhere and it doesn't depend on branch
create_yum_hosted('yum-tpc-binary', '0')
// hosted tpc source has build packages from third-party-packages repo and it doesn't depend on branch for now
// because contrail-third-party-packages doesn't have branches
create_yum_hosted('yum-tpc-source', '0')

// Maven
create_maven_hosted('maven-releases')
create_maven_hosted('maven-snapshots')
create_maven_hosted('vmware-releases')
create_maven_proxy('maven-central', 'https://repo1.maven.org/maven2')
create_maven_group('maven-public', ['maven-releases', 'maven-snapshots', 'maven-central', 'vmware-releases'])

// Remove web proxies if any
core.removeHTTPProxy()
core.removeHTTPSProxy()

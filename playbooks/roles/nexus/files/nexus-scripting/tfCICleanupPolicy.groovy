import org.sonatype.nexus.cleanup.storage.CleanupPolicyStorage
import org.sonatype.nexus.cleanup.storage.CleanupPolicy
import org.sonatype.nexus.cleanup.storage.CleanupPolicyCriteria
import static org.sonatype.nexus.cleanup.storage.CleanupPolicy.ALL_CLEANUP_POLICY_FORMAT;

// https://github.com/danischroeter/nexus-repo-scripting/blob/master/src/main/groovy/deleteOldComps.groovy
// https://github.com/danischroeter/nexus-repo-scripting/blob/master/src/main/groovy/detailRepoStats.groovy
// https://support.sonatype.com/hc/en-us/article_attachments/360027882734/nx-blob-repo-space-report.groovy


def create_or_update_cleanup_policy(name, format, lastBlobUpdated, lastDownloaded) {
    def storage = container.lookup(CleanupPolicyStorage.class.name)
    def cpc = new CleanupPolicyCriteria()
    cpc.lastBlobUpdated = lastBlobUpdated
    cpc.lastDownloaded = lastDownloaded
    def cpc_map = CleanupPolicyCriteria.toMap(cpc)
    def cp = storage.get(name)
    if (cp != null) {
        cp.setFormat(format)
        cp.setCriteria(cpc_map)
        storage.update(cp)
    } else {
        cp = new CleanupPolicy(
            name,                       // name
            '',                         // final String notes
            format,                     // final String format,
            '',                         // final String mode,
            cpc_map                     // final Map<String, String> criteria
        )
        storage.add(cp)
    }
}

create_or_update_cleanup_policy('tf-cleanup-policy', ALL_CLEANUP_POLICY_FORMAT, 1, 1)

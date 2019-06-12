import org.sonatype.nexus.scheduling.TaskConfiguration
import org.sonatype.nexus.scheduling.TaskInfo
import org.sonatype.nexus.scheduling.TaskScheduler
import org.sonatype.nexus.scheduling.schedule.Schedule

import org.sonatype.nexus.blobstore.api.BlobStoreManager
import org.sonatype.nexus.blobstore.compact.internal.CompactBlobStoreTaskDescriptor;


// https://www.tikalk.com/posts/2017/02/21/Automating-Nexus-repository-management/

def create_or_update_task(type_id, name, cron, task_properties) {
    TaskScheduler scheduler = container.lookup(TaskScheduler.class.name)
    TaskConfiguration task_config = null
    TaskInfo existing_task = scheduler.listsTasks().find { TaskInfo info ->
        info.name == name
    }
    if (existing_task != null) {
        task_config = existing_task.getConfiguration()
    } else {
        task_config = scheduler.createTaskConfigurationInstance(type_id)
    }
    task_config.setName(name)
    task_properties.each { key, value -> task_config.setString(key, value) }
    Schedule schedule = scheduler.scheduleFactory.cron(new Date(), cron)
    scheduler.scheduleTask(task_config, schedule)
}

def list_tasks() {

    TaskScheduler scheduler = container.lookup(TaskScheduler.class.name)
    scheduler.listsTasks().each { task_info -> 
        println(task_info)
        println('')
    }
}

def cron = '0 0 1 * * ?'
def compact_task_properties = [:] as Map
compact_task_properties.put(
    CompactBlobStoreTaskDescriptor.BLOB_STORE_NAME_FIELD_ID,
    BlobStoreManager.DEFAULT_BLOBSTORE_NAME)
create_or_update_task(
    CompactBlobStoreTaskDescriptor.TYPE_ID,
    'tf-ci-storage-compact',
    cron,
    compact_task_properties)

def gc_task_properties = [:] as Map
task_properties.put('repositoryName', 'tungsten_ci')
create_or_update_task(
    'repository.docker.gc',
    'tf-ci-tungsten_ci-gc',
    cron,
    gc_task_properties)

list_tasks()

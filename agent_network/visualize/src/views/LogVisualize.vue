<template>    
  <el-container width="1024px" height="100%">
    <el-header>
      <el-row>
        <el-col :span="12">Log Visualize</el-col>
        <el-col :span="12" style="text-align: right;">
          <el-upload
            ref="file_list"
            action=""
            :limit="1"
            :on-exceed="handleExceed"
            :on-change="load_file"
            :auto-upload="false"
          >
            <el-button type="primary">select file</el-button>
          </el-upload>
        </el-col>
      </el-row>
    </el-header>
    <el-container>
      <el-aside>
        <el-menu default-active="1" class="el-menu-vertical-demo">
          <el-menu-item
            v-for="instance in all_instance"
            :key="instance"
            :index="instance"
            @click="handleMenuClick(instance)"
          >
            {{ instance }}
          </el-menu-item>
        </el-menu>
      </el-aside>
      <el-main>
        <div v-if="cur_instance === 'All'">
          <div v-for="trace in trace_data" style="margin: 5px;">
            <el-card
              :style="{ backgroundColor: color[trace.instance] }"
            >
              <h3>{{ trace.instance }} - {{ trace.role }} - {{ trace.time }}</h3>
              <div v-html="trace.content"></div>
            </el-card>
          </div>
        </div>
        <div v-else>
            <div v-for="trace in catogrized_data[cur_instance]" style="margin: 5px;">
              <el-card
                :style="{ backgroundColor: color[trace.instance] }"
              >
                <h3>{{ trace.instance }} - {{ trace.role }} - {{ trace.time }}</h3>
                <div v-html="trace.content"></div>
              </el-card>
            </div>
        </div>
      </el-main>
    </el-container>
  </el-container>
</template>

<script lang="ts">
import { defineComponent, ref, reactive } from 'vue';
import { genFileId, TabsInstance } from 'element-plus';
import type { UploadInstance, UploadProps, UploadRawFile } from 'element-plus';
import MarkdownIt from 'markdown-it';
import mk from 'markdown-it-katex';

export default defineComponent({
  setup() {
    const file_list = ref<UploadInstance>();
    const trace_data = ref<any[]>();
    const catogrized_data = reactive<{ [key: string]: any[] }>({});
    const colors = ref<string[]>(["#409EFF", "#E6A23C", "#67C23A", "#909399"]); // blue green yellow grey
    const color_index = ref(0);
    const color = reactive<{ [kye: string]: string }>({"Agent-Network": "#FFFFFF"})

    const all_instance = ref<string[]>(["All"]);
    const cur_instance = ref("All");
    const tabPosition = ref<TabsInstance['tabPosition']>('left')

    const handleExceed: UploadProps['onExceed'] = (files) => {
      file_list.value!.clearFiles()
      const file = files[0] as UploadRawFile
      file.uid = genFileId()
      file_list.value!.handleStart(file)
    };

    const load_file = (file: UploadProps["onChange"]) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        if (typeof e.target.result  === "string") {
          trace_data.value = JSON.parse(e.target.result);
          trace_data.value.forEach(trace => {
            trace["content"] = render_md(trace["content"]);
            trace["time"] = formatTimestamp(Number(trace["time"]) * 1000);
          });
          console.log(trace_data.value);
          catogrize_trace();
        }
      };

      reader.readAsText(file.raw!);
    };

    const catogrize_trace = () => {
      trace_data.value.forEach(trace => {
        if (trace["instance"] in catogrized_data) {
          catogrized_data[trace["instance"]].push(trace);
        } else {  
          catogrized_data[trace["instance"]] = [trace];
          all_instance.value.push(trace["instance"]);
          console.log(trace["instance"]);
          if (trace["instance"] != "Agent-Network") {
            color[trace["instance"]] = colors.value[color_index.value];
            color_index.value = (color_index.value + 1) % colors.value.length;
          }
        }
      });
    };

    const formatTimestamp = (timestamp: number) => {
      console.log(timestamp);
      // 创建一个新的Date对象
      const date = new Date(timestamp);

      // 获取小时、分钟和秒
      const hours = date.getHours().toString().padStart(2, '0');
      const minutes = date.getMinutes().toString().padStart(2, '0');
      const seconds = date.getSeconds().toString().padStart(2, '0');

      // 将小时、分钟和秒组合成一个字符串
      return `${hours}:${minutes}:${seconds}`;
    }

    const render_md = (content: string) => {
      const md = new MarkdownIt();
      md.renderer.rules.softbreak = () => "<br>";
      md.use(mk);
      return md.render(content);
    }

    const handleMenuClick = (instance: string) => {
      cur_instance.value = instance;
    };

    return {
      file_list,
      trace_data,
      catogrized_data,
      color,
      all_instance,
      cur_instance,
      tabPosition,
      handleExceed,
      load_file,
      catogrize_trace,
      formatTimestamp,
      render_md,
      handleMenuClick
    };
  },
});
</script>
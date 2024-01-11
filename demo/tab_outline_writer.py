import json
import gradio as gr

from demo.gr_utils import messages2chatbot, block_diff_text


def tab_outline_writer(config):
    lngpt = config['lngpt']
    FLAG = {
        'running': 0,
        'cancel': 0,
    }
    volume_name, chapter_name = None, None
    def get_writer():
        nonlocal lngpt
        lngpt = config['lngpt']
        if not lngpt:
            return None
        return lngpt.get_writer(volume_name, chapter_name)

    with gr.Tab("生成大纲") as tab:
        def create_novel_name():
            if not get_writer():
                return gr.Radio(choices=["请先在<选择小说名>页面中选择小说。", ], label="选择小说：", value="请先在<选择小说名>页面中选择小说。")
            
            return gr.Radio(
                choices=[config['novel_name'], ],
                label="选择小说：",
                value=""
            )
        
        novel_name = gr.Radio()
        
        with gr.Row():
            

            with gr.Column():
                def get_inputs_text():
                    return get_writer().get_custom_system_prompt()

                inputs = gr.Textbox(label="这是一部什么样的小说？", lines=10, interactive=False)

            def get_output_text():
                return get_writer().json_dumps(get_writer().outline)

            output = gr.Textbox(label="生成的小说大纲", lines=10, interactive=False)


        def create_option(value):
            available_options = ["创作小说设定", ]
            if get_writer().has_chat_history('instruction_outline'):
                available_options.append("创作分卷剧情")

            return gr.Radio(
                choices=available_options,
                label="选择你要进行的操作",
                value='',
            )
        model = gr.Radio(choices=[('gpt-3.5-turbo', 'gpt-3.5-turbo-1106'), ('gpt-4-turbo', 'gpt-4-1106-preview')], label="选择模型")
        
        option = gr.Radio()

        def create_sub_option(option_value):
            return gr.Radio(["全部章节"], label="选择章节", value="", visible=False)

        sub_option = gr.Radio()

        def create_human_feedback(option_value):
            human_feedback_string = ''
            writer = get_writer()
            if option_value == '创作小说设定':
                if writer.outline:
                    human_feedback_string = writer.get_config("refine_outline_setting")
                else:
                    human_feedback_string = writer.get_config("init_outline_setting")
            elif option_value == '创作分卷剧情':
                if '分卷剧情' in writer.outline:
                    human_feedback_string = writer.get_config("refine_outline_volumes")
                else:
                    human_feedback_string = writer.get_config("init_outline_volumes")

            return gr.Textbox(value=human_feedback_string, label="你的意见：", lines=2, placeholder="让AI知道你的意见。")
        
        human_feedback = gr.Textbox()

        def on_select_option(evt: gr.SelectData):
            return create_sub_option(evt.value), create_human_feedback(evt.value)

        option.select(on_select_option, None, [sub_option, human_feedback])

        def generate_cost_info(cur_messages):
            cost = cur_messages.cost
            return gr.Markdown(f"当前操作预计消耗：{cost:.4f}$")

        cost_info = gr.Markdown('当前操作预计消耗：0$')
        start_button = gr.Button("开始")
        rollback_button = gr.Button("撤销")

        chatbot = gr.Chatbot()

        def check_running(func):
            def wrapper(*args, **kwargs):
                if FLAG['running'] == 1:
                    gr.Info("当前有操作正在进行，请稍后再试！")
                    return

                FLAG['running'] = 1
                try:
                    for ret in func(*args, **kwargs):
                        if FLAG['cancel']:
                            FLAG['cancel'] = 0
                            break
                        yield ret
                except Exception as e:
                    raise gr.Error(e)
                finally:
                    FLAG['running'] = 0
            return wrapper
        
        @check_running
        def on_submit(option, sub_option, human_feedback):
            if not option:
                gr.Info("请先选择操作！")
                return
              
            match option:
                case '创作小说设定':
                    for messages in get_writer().init_outline_setting(human_feedback=human_feedback):
                        yield messages2chatbot(messages), generate_cost_info(messages)
                case '创作分卷剧情':
                    for messages in get_writer().init_outline_volumes(human_feedback=human_feedback):
                        yield messages2chatbot(messages), generate_cost_info(messages)
        
        def save():
            lngpt.save(volume_name, chapter_name)
    
        def rollback(i):
            return lngpt.rollback(i, volume_name, chapter_name)  
        
        def on_roll_back():
            if FLAG['running'] == 1:
                FLAG['cancel'] = 1
                gr.Info("已暂停当前操作！")
                return

            if rollback(1):
                gr.Info("撤销成功！")
            else:
                gr.Info("已经是最早的版本了")
        
        @gr.on(triggers=[model.select, option.select, human_feedback.change], inputs=[model, option, sub_option, human_feedback], outputs=[chatbot, cost_info])
        def on_cost_change(model, option, sub_option, human_feedback):
            get_writer().set_model(model)
            if option:
                messages, cost_info = next(on_submit(option, sub_option, human_feedback))
                return messages, cost_info
            else:
                return None, None

        start_button.click(on_submit, [option, sub_option, human_feedback], [chatbot, cost_info]).success(
            save).then(
            lambda option: (get_output_text(), create_option(''), create_sub_option(option)), option, [output, option, sub_option]
        )

        rollback_button.click(on_roll_back, None, None).success(
            lambda option: (get_output_text(), create_option(''), create_sub_option(option), []), option, [output, option, sub_option, chatbot]
        )
    
    novel_name.select(
        lambda novel_name: (get_inputs_text(), get_output_text(), create_option(''), create_sub_option(''), []), novel_name, [inputs, output, option, sub_option]
        )
    
    tab.select(lambda : create_novel_name(), None, novel_name).then(
        lambda : (gr.Textbox(''), gr.Textbox(''), gr.Radio([]), gr.Radio([]), []), None, [inputs, output, option, sub_option, chatbot]
        )
    